import inspect
import sys
import traceback
from types import ModuleType
from typing import List, Union

from more_termcolor import colors

FrameSummaries = List[List[Union[int, traceback.FrameSummary]]]


class ExcHandler:
    def __init__(self, exc: Exception = None, *, capture_locals=True, formatter=repr):
        """
        Provides additional data about the exception with extra functionality, including frame locals. Example:
        ::
            except Exception as e:
                print(ExcHandler(e).full())
                """
        # TODO: 1. support for *args then print arg names and values like in 'printdbg'
        #  2. handle 'raise ... from e' better. 'Responsible code: raise ...' isnt interesting (use e.__cause__)
        #  3. if exception raised deliberately ("raise ValueError(...)"), get earlier frame
        self.exc = None  # declare first thing in case anything fails
        self._formatter = formatter
        try:
            
            if exc:
                tb = sys.exc_info()[2]  # only tb because caller passed exc
                self.exc = exc
            else:
                _, exc, tb = sys.exc_info()  # exc and tb
                self.exc = exc
            self.excArgs = ""
            self.frame_summaries: FrameSummaries = []
            
            if not tb and not exc:
                return
            
            tb_frame_summaries = ExcHandler._extract_tb(tb, capture_locals)
            stack: traceback.StackSummary = traceback.extract_stack()[:-1]  # leave out current frame
            self.frame_summaries = ExcHandler._combine_traceback_and_stack(stack, tb_frame_summaries)
            self.excArgs = ExcHandler.fmt_args(self.exc.args)
        
        except Exception as init_exc:
            self._handle_self_failure(init_exc)
    
    @staticmethod
    def _handle_bad_call_context():
        warning = '\n'.join(["ExcHandler couldn't find any Exception along the trace",
                             "You probably called logger.exception() not inside an exception handling block",
                             "(could also happen when calling logger.error(summarize_exc=True) outside exc handling block"])
        print(warning)
        return ""
    
    def _handle_self_failure(self, init_exc):
        # TODO: this only partially works, needs some work
        tb = sys.exc_info()[2]
        stack: traceback.StackSummary = traceback.extract_stack()[:-2]  # leave out this frame and __init__ frame
        innerframes = inspect.getinnerframes(tb)
        outerframes = inspect.getouterframes(innerframes[0].frame)[1:]  # outerframes are in reverse order
        orig_frame = outerframes[0].frame
        self.frame_summaries = ExcHandler._remove_nonlib_frames(stack)
        self.last.locals = orig_frame.f_locals
        
        if not self.exc:
            try:
                orig_exc = next(val for name, val in self.last.locals.items() if isinstance(val, Exception))  # calculated guess
            except StopIteration:
                orig_exc = None
            self.exc = orig_exc
        args = '\n\t'.join([f'ExcHandler.__init__() ITSELF failed, accidental exception (caught and ok):',
                            f'{init_exc.__class__.__qualname__}: {ExcHandler.fmt_args(init_exc.args)}',
                            f'ORIGINAL exception: {self.excType}: {self.exc}'
                            ])
        self.excArgs = args
    
    @staticmethod
    def _extract_tb(tb, capture_locals: bool) -> FrameSummaries:
        
        extracted_tb = traceback.extract_tb(tb)
        tb_frame_summaries: FrameSummaries = ExcHandler._remove_nonlib_frames(extracted_tb)
        if capture_locals:
            tb_steps_taken = 0
            for i, (f_idx, frame) in enumerate(tb_frame_summaries):
                if f_idx == tb_steps_taken:
                    tb_frame_summaries[i][1].locals = tb.tb_frame.f_locals
                    tb = tb.tb_next
                    tb_steps_taken += 1
                    continue
                
                if f_idx < tb_steps_taken:
                    print(colors.brightyellow(f'REALLY WIERD, f_idx ({f_idx}) < tb_steps_taken ({tb_steps_taken})'))
                    continue
                
                if f_idx > tb_steps_taken:
                    steps_to_take = f_idx - tb_steps_taken
                    for _ in range(steps_to_take):
                        tb = tb.tb_next
                        tb_steps_taken += 1
                tb_frame_summaries[i][1].locals = tb.tb_frame.f_locals
                tb = tb.tb_next
                tb_steps_taken += 1
        
        return tb_frame_summaries
    
    @staticmethod
    def _combine_traceback_and_stack(stack: traceback.StackSummary, tb_frame_summaries: FrameSummaries) -> FrameSummaries:
        """The traceback has specific info regarding the exceptions.
        The stack has unspecific info regarding the exceptions, plus info about everything preceding the exceptions.
        This function combines the two."""
        stack_frame_summaries: FrameSummaries = ExcHandler._remove_nonlib_frames(stack)
        overlap_index = ExcHandler._get_frames_overlap_index(stack_frame_summaries, tb_frame_summaries)
        if overlap_index is not None:
            stack_frame_summaries[overlap_index:] = tb_frame_summaries
        else:
            stack_frame_summaries.extend(tb_frame_summaries)
        return stack_frame_summaries
    
    @staticmethod
    def _remove_nonlib_frames(stack: traceback.StackSummary) -> FrameSummaries:
        frame_summaries: FrameSummaries = []
        for i, frame in enumerate(stack):
            irrelevant = 'site-packages' in frame.filename or 'dist-packages' in frame.filename or 'python3' in frame.filename or 'JetBrains' in frame.filename
            if irrelevant:
                continue
            frame_summaries.append([i, frame])
        return frame_summaries
    
    @staticmethod
    def _get_frames_overlap_index(stack_f_summaries: FrameSummaries, tb_f_summaries: FrameSummaries):
        # tb sort: most recent first. stack sort is the opposite → looking to match tb_f_summaries[0]
        for i, fs in enumerate(stack_f_summaries):
            if fs[1].filename == tb_f_summaries[0][1].filename:
                return i
        return None
    
    @staticmethod
    def fmt_args(exc_args) -> str:
        excArgs = []
        for arg in map(str, exc_args):
            if len(arg) > 500:
                arg = f'{arg[:500]}...'
            excArgs.append(arg)
        return ", ".join(excArgs)
    
    def _format_locals(self, lokals: dict) -> str:
        formatted = ""
        for name, val in lokals.items():
            if name.startswith('__') or isinstance(val, ModuleType):
                continue
            if inspect.isfunction(val):
                print(colors.brightblack(f'skipped function: {name}'))
                continue
            
            typ = self._formatter(type(val))
            val = self._formatter(val)
            
            if val.startswith('typing'):
                continue
            if '\n' in val:
                linebreak = '\n\n'  # queries etc
                quote = '"""'
            else:
                linebreak = '\n'
                quote = ''
            formatted += f'\t{name}: {quote}{val}{quote} {colors.dark(typ)}{linebreak}'
        return formatted
    
    @property
    def last(self) -> traceback.FrameSummary:
        try:
            return self.frame_summaries[-1][1]
        except Exception as e:
            print('FAILED getting ExcHandler.last()\n', ExcHandler(e).summary())
            fs = traceback.FrameSummary(__name__, -1, 'ExcHandler.last()')
            return fs
    
    @property
    def excType(self):
        return self.exc.__class__.__qualname__
    
    def shorter(self, *extra):
        """Returns 1 very short line: just pretty exception type and formatted exception args if exist"""
        if not self.exc:
            return ExcHandler._handle_bad_call_context()
        if self.excArgs:
            string = f"{self.excType}: {self.excArgs}"
        else:
            string = self.excType
        if extra:
            string += f' | ' + ', '.join(map(str,extra))
        return string
    
    def short(self, *extra):
        """Returns 1 line: exc args and some context info"""
        if not self.exc:
            return ExcHandler._handle_bad_call_context()
        string = f'{self.excType}: {self.excArgs} | File "{self.last.filename}", line {self.last.lineno} in {colors.brightwhite(self.last.name)}()'
        if extra:
            string += f' | ' + ', '.join(map(str, extra))
        return string
    
    def summary(self, *extra):
        """Returns 5 lines"""
        if not self.exc:
            return ExcHandler._handle_bad_call_context()
        string = '\n'.join([f'{self.excType}, File "{self.last.filename}", line {self.last.lineno} in {colors.brightwhite(self.last.name)}()',
                            f'Exception args:',
                            f'\t{self.excArgs}',
                            f'Responsible code:',
                            f'\t{self.last.line}',
                            *map(str, extra)
                            ])
        
        return string
    
    def full(self, *extra, limit: int = None):
        """Prints the summary, whole stack and local variables at the scope of exception.
        Limit is 0-based, from recent to deepest (limit=0 means only first frame)"""
        import os
        try:
            termwidth, _ = os.get_terminal_size()
            print(f'termwidth: {termwidth}')
            if not termwidth:
                termwidth = 80
        except Exception as e:
            termwidth = 80
        if not self.exc:
            return ExcHandler._handle_bad_call_context()
        description = self.summary(*extra)
        honor_limit = limit is not None
        for i, fs in self.frame_summaries:
            if honor_limit and i > limit:
                break
            # from recent to deepest
            description += f'\nFile "{fs.filename}", line {fs.lineno} in {colors.brightwhite(fs.name + "()")}\n\t{fs.line}'
            if fs.locals is not None:
                description += f'\nLocals:\n{self._format_locals(fs.locals)}'
        return f'\n{"-" * termwidth}\n\n{description}\n{"-" * termwidth}\n'
