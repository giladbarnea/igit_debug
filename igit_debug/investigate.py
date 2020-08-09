import inspect
from typing import Callable, List

import functools
from more_termcolor import colors

import igit_debug.formatting
from . import ExcHandler


# * debug utils
# https://github.com/mahmoud/boltons
#  specifically: https://github.com/mahmoud/boltons/blob/41a926e64ff69e152d14dff87a2766b27ae2b53b/boltons/debugutils.py#L118
# https://github.com/tensorflow/tensorflow/blob/master/tensorflow/python/debug/lib/debug_utils.py
# https://github.com/KrazyKode101/python-debug-utils
# https://github.com/alikins/python-debug-utils
# https://pypi.org/project/python-debug/
class PrettySig(dict):
    def __init__(self, fn, fn_arg_values, fn_kwargs, *, types=False):
        """Create a pretty str representation of the function signature, formatting the arg names, values [and types]."""
        super().__init__()
        spec = inspect.getfullargspec(fn)
        arg_names = spec.args
        
        # prepare function default values
        if spec.defaults:
            arg_defaults = dict(zip(arg_names[-len(spec.defaults):], spec.defaults))
        else:
            arg_defaults = dict()
        self.update(**fn_kwargs, **arg_defaults)
        # format positional args with their respective passed values
        if types:
            _pretty_val = lambda _v: f'{igit_debug.formatting.pformat(_v)} {colors.dark(igit_debug.formatting.pformat(type(_v)))}'
        else:
            _pretty_val = lambda _v: igit_debug.formatting.pformat(_v)
        args_str = ''
        for k, v in zip(arg_names, fn_arg_values):
            self[k] = v
            args_str += f'{k}: {_pretty_val(v)}, '
        
        if len(arg_names) < len(fn_arg_values):
            # what's this?
            args_str += ', ' + ', '.join(map(igit_debug.formatting.pformat, fn_arg_values[-len(arg_names):]))
        
        # we're left with:
        # (1) positional args (with default values), that were omitted by the caller
        # (2) keyworded args that were passed by the caller
        # (3) keyworded args (with default values), that were omitted by the caller
        
        remaining_arg_names = arg_names[len(fn_arg_values):]
        fn_kwargs_copy = dict(fn_kwargs)
        self.update(**fn_kwargs)
        # handle (1) and (2)
        for a in remaining_arg_names:
            # TODO: types
            if a in fn_kwargs_copy:
                args_str += f', {a}={igit_debug.formatting.pformat(fn_kwargs_copy[a])}'
                del fn_kwargs_copy[a]
            elif a in arg_defaults:
                args_str += f', {a}={igit_debug.formatting.pformat(arg_defaults[a])}'
        
        # handle (3)
        if fn_kwargs_copy:
            for k, v in fn_kwargs_copy.items():
                args_str += f', {k}={igit_debug.formatting.pformat(v)}'
        self.pretty_repr = args_str
    
    def __getattribute__(self, item):
        try:
            return super().__getattribute__(item)
        except AttributeError as e:
            return self.get(item)
    
    def __str__(self):
        return self.pretty_repr
    
    __repr__ = __str__


def _pretty_retval(retval, *, types=False):
    pretty = igit_debug.formatting.pformat(retval)
    if len(pretty) > 300:  # don't clutter
        pretty = f'{pretty[:300]}...'
    elif types:
        pretty += colors.dark(f' {igit_debug.formatting.pformat(type(retval))}')
    return pretty


def logreturn(fn):
    identifier = fn.__qualname__
    
    @functools.wraps(fn)
    def decorator(*fn_args, **fn_kwargs):
        retval = fn(*fn_args, **fn_kwargs)
        pretty = _pretty_retval(retval, types=True)
        print(f'{identifier}() returning → {pretty}')
        return retval
    
    return decorator


# TODO: make all of these Loggr methods
def loginout(_fn=None, *, types=False):
    def wrapper(fn):
        identifier = fn.__qualname__
        
        @functools.wraps(fn)
        def decorator(*fn_args, **fn_kwargs):
            prettysig = PrettySig(fn, fn_args, fn_kwargs)
            sig_repr = repr(prettysig)
            if not sig_repr:
                sig_repr = '<no args>'
            retval = fn(*fn_args, **fn_kwargs)
            pretty = _pretty_retval(retval, types=types)
            print(f'{identifier}({sig_repr}) → {pretty}')
            return retval
        
        return decorator
    
    if _fn is None:
        return wrapper
    return wrapper(_fn)


def logonreturn(*variables, types=False):
    """@logonreturn('self.answer', types=True)"""
    
    def wrapper(fn):
        identifier = fn.__qualname__
        
        @functools.wraps(fn)
        def decorator(*fn_args, **fn_kwargs):
            retval = fn(*fn_args, **fn_kwargs)
            # if not variables:
            #     print(colors.brightyellow(f'logonreturn({identifier}) no variables. returning retval as-is'))
            #     return retval
            prettysig = PrettySig(fn, fn_args, fn_kwargs, types=types)
            obj = prettysig
            for var in variables:
                attrs = var.split('.')
                for attr in attrs:
                    obj = obj.__getattribute__(attr)
            print(f'{var}: {igit_debug.formatting.pformat(obj, types=types)}')
            return retval
        
        return decorator
    
    return wrapper


def getvarnames(*vars) -> dict:
    varnames = dict()
    currframe = inspect.currentframe()
    outer = inspect.getouterframes(currframe)
    frameinfo = outer[2]  # self check: ctx has 'varnames=True'
    
    ctx = frameinfo.code_context[0].strip()
    open_parens = 0
    last_close_i = None
    for i, c in enumerate(reversed(ctx), 1):
        if c == ')':
            last_close_i = i
            open_parens -= 1
        elif c == '(':
            open_parens += 1
            if open_parens == 0:
                fn_args_str = ctx[-i + 1:-last_close_i].replace(' ', '')
                argnames = fn_args_str.split(',')
                for arg in argnames[:]:
                    if arg.startswith('types=') or arg.startswith('varnames='):
                        argnames.remove(arg)
                break
    else:
        # no argnames!
        breakpoint()
    
    # argnames = ctx[ctx.find('(') + 1:-1].split(', ')
    if len(argnames) != len(vars):
        print(f"Too complex statement, try breaking it down to variables or eliminating whitespace",
              # f'len(argnames): {len(argnames)}', f'len(args): {len(args)}', f'len(kwargs): {len(kwargs)}',
              # vprint(ctx, argnames, args, kwargs)
              )
        # return
    
    for i, val in enumerate(vars):
        try:
            name = argnames[i].strip()
        except IndexError:
            continue  # TODO: break?
        varnames[name] = val
    return varnames


def vprint(*args, apply=print, **kwargs):
    """
    Prints the variable name, its type and value.
    ::
        vprint(5 + 5, sum([1,2]))
        > 5 + 5 (<class 'int'>):
          10

          sum([1,2]) (<class 'int'>):
          3

    """
    
    def printarg(_name, _val) -> str:
        _string = f'{_name}: {igit_debug.formatting.pformat(_val, types=True)}'
        apply(_string)
        return _string
    
    strings = []
    if args:
        currframe = inspect.currentframe()
        outer = inspect.getouterframes(currframe)
        frameinfo = outer[1]
        ctx = frameinfo.code_context[0].strip()
        argnames = ctx[ctx.find('(') + 1:-1].split(', ')
        if len(argnames) != len(args) + len(kwargs):
            print(f"Too complex statement, try breaking it down to variables or eliminating whitespace",
                  # f'len(argnames): {len(argnames)}', f'len(args): {len(args)}', f'len(kwargs): {len(kwargs)}',
                  # vprint(ctx, argnames, args, kwargs)
                  )
            # return
        
        for i, val in enumerate(args):
            try:
                name = argnames[i].strip()
            except IndexError:
                continue  # TODO: break?
            strings.append(printarg(name, val))
    for name, val in kwargs.items():
        strings.append(printarg(name, val))
    # return strings


def investigate(*,
                args=True,
                ret_val=True,
                print_exc=True,
                locals_on_return=False,
                formatter: Callable = igit_debug.formatting.pformat,
                raise_on_exc=True,
                types=False):
    """
    A decorator that logs common debugging information, like formatted exceptions before they're thrown, argument names and values, return value etc.
    ::
        @logger.investigate(locals_on_return=True)
        def foo(bar):
            ...
    """
    
    # * similar function: https://github.com/zopefoundation/AccessControl/blob/master/src/AccessControl/requestmethod.py
    def wrapper(fn):
        
        def decorator(*fn_args, **fn_kwargs):
            fnname = fn.__qualname__
            if '.' in fnname:
                identifier = fnname
            else:
                identifier = f'{inspect.getmodulename(inspect.getmodule(fn).__file__)}.{fnname}'
            if args:
                # create a pretty str representation of the function arguments
                prettysig = PrettySig(fn, fn_args, fn_kwargs)
                sig_repr = repr(prettysig)
                if not sig_repr:
                    sig_repr = 'no args'
                print(f'entered {identifier}({sig_repr})')
            else:
                print(f'entered {identifier}()')
            try:
                retval = fn(*fn_args, **fn_kwargs)
                if ret_val:
                    
                    if locals_on_return:
                        # try:
                        #     raise Exception("dummy")
                        # except Exception as e:
                        #     hdlr = ExcHandler(e)
                        # ins_stack = inspect.stack()
                        # tb_stack: traceback.StackSummary = traceback.extract_stack()
                        # tb_stack = ExcHandler._remove_nonlib_frames(tb_stack)
                        pass
                    pretty = _pretty_retval(retval, types=types)
                    print(f'{identifier}() returning → {pretty}')
                
                else:
                    print(f'exiting {identifier}()')
                
                return retval
            except Exception as e:
                if print_exc:
                    e_handler = ExcHandler(e)
                    print(colors.brightred(e_handler.full()))
                if raise_on_exc:
                    raise e
        
        return decorator
    
    return wrapper


def caller():
    frame = inspect.currentframe()
