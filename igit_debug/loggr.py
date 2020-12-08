import os

IGIT_LOG_LEVEL = os.environ.get('IGIT_LOG_LEVEL', '')
if IGIT_LOG_LEVEL.lower() == 'none':
    class Loggr:
        def __init__(self, *args, **kwargs):
            pass
        
        def __getattribute__(self, item):
            return self
        
        def __call__(self, *args, **kwargs):
            return self
else:
    import sys
    from time import perf_counter
    
    ts0 = perf_counter()
    from typing import Callable, Any, Tuple
    
    ts1 = perf_counter()
    print(f'igit_debug.loggr.py | importing from typing took {round((ts1 - ts0) * 1000, 2)}ms')
    ts2 = perf_counter()
    import logbook
    from logbook import Logger
    
    ts3 = perf_counter()
    print(f'igit_debug.loggr.py | importing logbook stuff took {round((ts3 - ts2) * 1000, 2)}ms')  # 45.15ms
    ts4 = perf_counter()
    from more_termcolor import colors
    
    ts5 = perf_counter()
    print(f'igit_debug.loggr.py | "from more_termcolor import colors" took {round((ts5 - ts4) * 1000, 2)}ms')
    import os
    from contextlib import suppress
    import functools
    
    ts6 = perf_counter()
    from .formatting import pformat
    from .investigate import PrettySig, getvarnames
    from .util import parse_level
    
    ts7 = perf_counter()
    print(f'igit_debug.loggr.py | "from . import ..." stmts took {round((ts7 - ts6) * 1000, 2)}ms')
    ts8 = perf_counter()
    import inspect
    
    ts9 = perf_counter()
    print(f'igit_debug.loggr.py | import inspect took {round((ts9 - ts8) * 1000, 2)}ms')
    
    
    # LOG_LEVEL = os.getenv('IGIT_LOG_LEVEL', NOTSET)
    
    def fmt_arg(arg, *, types=False) -> str:
        """Underlines args ending with ':'.
        Applies `pformat` on `arg`."""
        with suppress(AttributeError):
            if arg.endswith(':'):
                types = False
        
        string = pformat(arg, types=types)
        
        if string.endswith(':'):
            return colors.ul(string[:-1]) + ': '
        else:
            return string + ', '
    
    
    def fmt_args(args: Tuple, *, types=False, varnames=False) -> str:
        """Splits `args` to separate lines if the resulting string is longer than 80.
        Applies `fmt_arg` to each `arg`."""
        formatted_args = [fmt_arg(a, types=types) for a in args]
        if len(args) > 1:
            sumlen = 0
            for i, arg in enumerate(args):
                try:
                    sumlen += len(arg)
                except TypeError:
                    # None has no len etc
                    # TODO: FormattedArg class with 'nocolor' prop and 'colored' prop
                    #  because formatted has extra ansi strings
                    sumlen += len(str(arg))
            # sumlen = sum(map(len, args))
            if sumlen <= 80:
                joined = ''.join(formatted_args).strip()
            
            else:
                joined = '\n' + '\n'.join(formatted_args).strip()
        else:
            joined = ''.join(formatted_args).strip()
        
        if joined.endswith(',') or joined.endswith(':'):
            return joined[:-1]
    
    
    def log_preprocess(fn: Callable[['Loggr', str, Any], None]):
        # TODO: implement so this:
        # logger.title(f'TrichDay.post(%prop, val, date%)')
        # is equivalent to this:
        # logger.title(f'TrichDay.post(prop={repr(prop)}, val={repr(val)}, date={repr(date)})')
        def logwrap(selfarg: 'Loggr', *args, **kwargs):
            """From kwargs:
             only_verbose, types, varnames, frame_correction.
             
             From env:
             IGIT_VERBOSE
            """
            verbose = os.getenv('IGIT_VERBOSE', False)
            if kwargs.get('only_verbose'):
                if not verbose:
                    return
                kwargs.pop('only_verbose')
            
            if selfarg.only_verbose and not verbose:
                return
            types = kwargs.get('types', False)
            varnames = kwargs.get('varnames', False)
            if varnames:
                vnames: dict = getvarnames(*args)
                args = []
                for name, value in vnames.items():
                    args.append(f'{name}:')
                    args.append(value)
            msg = fmt_args(args, types=types, varnames=varnames)
            if (frame_correction := kwargs.get('frame_correction')) is None:
                kwargs['frame_correction'] = 2
            else:
                kwargs['frame_correction'] = int(frame_correction) + 2
            return fn(selfarg, msg, **kwargs)
        
        return logwrap
    
    
    class Loggr(Logger):
        
        def __init__(self, name=None, level=os.getenv('IGIT_LOG_LEVEL', 'NOTSET'), *, only_verbose=False):
            """'info' is higher than 'debug'.
            frame_correction=2, only_verbose=False, types=False, varnames=False.
            :param bool only_verbose:
            """
            print(f"Loggr __init__, level: {level}, only_verbose: {only_verbose}")
            level = parse_level(level)
            super().__init__(name, level)
            self.only_verbose = only_verbose
        
        @log_preprocess
        def debug(self, msg, **kwargs):
            if '\x1b[' in msg:
                # TODO: remove when more_termcolor test__multiple_scopes test__real_world__loggr passes
                super().debug(msg, **kwargs)
            else:
                super().debug(colors.dark(msg), **kwargs)
        
        @log_preprocess
        def info(self, msg, **kwargs):
            super().info(colors.white(msg), **kwargs)
        
        @log_preprocess
        def good(self, msg, **kwargs):
            super().info(colors.green(msg), **kwargs)
        
        @log_preprocess
        def warn(self, msg, **kwargs):
            super().warn(colors.yellow(msg), **kwargs)
        
        warning = warn
        
        @log_preprocess
        def boldwarn(self, msg, **kwargs):
            super().warn(colors.yellow(msg, 'bold'), **kwargs)
        
        @log_preprocess
        def error(self, msg, **kwargs):
            super().error(colors.red(msg), **kwargs)
        
        def exception(self, *args, **kwargs):
            super().exception(colors.brightred(args[0]), *args[1:], **kwargs)
        
        @log_preprocess
        def title(self, msg, **kwargs):
            super().info(colors.white(msg, 'bold'), **kwargs)
        
        def bylevel(self, msg, *, level, **kwargs):
            try:
                fn = getattr(self, level.lower())
            except AttributeError as e:
                fn = self.debug
            return fn(msg, **kwargs)
        
        # ** decorators
        def logonreturn(self, *variables, types=False, level='DEBUG'):
            """@logonreturn('self.answer', types=True)
            Currently only works for args passed in signatures"""
            
            def wrapper(fn):
                identifier = fn.__qualname__
                
                @functools.wraps(fn)
                def decorator(*fn_args, **fn_kwargs):
                    retval = fn(*fn_args, **fn_kwargs)
                    # if not variables:
                    #     print(colors.brightyellow(f'logonreturn({identifier}) no variables. returning retval as-is'))
                    #     return retval
                    # TODO:
                    #  if var is not found, try get fn locals
                    #  file = inspect.getsourcefile(fn)
                    #  f = next frame in sys._getframe(n) if file in str(frame)
                    #
                    prettysig = PrettySig(fn, fn_args, fn_kwargs, types=types)
                    obj = prettysig
                    for var in variables:
                        attrs = var.split('.')
                        for attr in attrs:
                            obj = obj.__getattribute__(attr)
                    self.bylevel(f'{var}: {pformat(obj, types=types)}', level=level)
                    return retval
                
                return decorator
            
            return wrapper
    
    
    ts10 = perf_counter()
    logbook.StreamHandler(sys.stdout, format_string='{record.time:%T.%f} | {record.module}.{record.func_name}() | {record.message}').push_application()
    ts11 = perf_counter()
    print(f'igit_debug.loggr.py | logbook.StreamHandler(...).push_application() took {round((ts11 - ts10) * 1000, 2)}ms')
    # logbook.FileHandler()
