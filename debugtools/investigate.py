import inspect
from typing import Callable

import functools
from more_termcolor import colors
from . import ExcHandler, loggr


# * debug utils
# https://github.com/mahmoud/boltons
#  specifically: https://github.com/mahmoud/boltons/blob/41a926e64ff69e152d14dff87a2766b27ae2b53b/boltons/debugutils.py#L118
# https://github.com/tensorflow/tensorflow/blob/master/tensorflow/python/debug/lib/debug_utils.py
# https://github.com/KrazyKode101/python-debug-utils
# https://github.com/alikins/python-debug-utils
# https://pypi.org/project/python-debug/

def _pretty_retval(retval, *, types=False):
    pretty = loggr.pformat(retval)
    if len(pretty) > 300:  # don't clutter
        pretty = f'{pretty[:300]}...'
    elif types:
        pretty += colors.dark(f' {loggr.pformat(type(retval))}')
    return pretty


def _pretty_sig(fn, fn_arg_values, fn_kwargs, *, types=False) -> str:
    """Create a pretty str representation of the function signature, formatting the arg names, values [and types]."""
    spec = inspect.getfullargspec(fn)
    arg_names = spec.args
    
    # prepare function default values
    if spec.defaults:
        arg_defaults = dict(zip(arg_names[-len(spec.defaults):], spec.defaults))
    else:
        arg_defaults = dict()
    
    # format positional args with their respective passed values
    if types:
        _pretty_val = lambda _v: f'{loggr.pformat(_v)} {colors.dark(loggr.pformat(type(_v)))}'
    else:
        _pretty_val = lambda _v: loggr.pformat(_v)
    args_str = ", ".join([f'{k}={_pretty_val(v)}' for k, v in zip(arg_names, fn_arg_values)])
    
    if len(arg_names) < len(fn_arg_values):
        # what's this?
        args_str += ', ' + ', '.join(map(loggr.pformat, fn_arg_values[-len(arg_names):]))
    
    # we're left with:
    # (1) positional args (with default values), that were omitted by the caller
    # (2) keyworded args that were passed by the caller
    # (3) keyworded args (with default values), that were omitted by the caller
    
    remaining_arg_names = arg_names[len(fn_arg_values):]
    fn_kwargs_copy = dict(fn_kwargs)
    # handle (1) and (2)
    for a in remaining_arg_names:
        # TODO: types
        if a in fn_kwargs_copy:
            args_str += f', {a}={loggr.pformat(fn_kwargs_copy[a])}'
            del fn_kwargs_copy[a]
        elif a in arg_defaults:
            args_str += f', {a}={loggr.pformat(arg_defaults[a])}'
    
    # handle (3)
    if fn_kwargs_copy:
        for k, v in fn_kwargs_copy.items():
            args_str += f', {k}={loggr.pformat(v)}'
    return args_str


def logreturn(fn):
    identifier = fn.__qualname__
    
    @functools.wraps(fn)
    def decorator(*fn_args, **fn_kwargs):
        retval = fn(*fn_args, **fn_kwargs)
        pretty = _pretty_retval(retval)
        print(colors.green(f'{identifier}() returning → {pretty}'))
        return retval
    
    return decorator


def loginout(_fn=None, *, types=False):
    def wrapper(fn):
        identifier = fn.__qualname__
        
        @functools.wraps(fn)
        def decorator(*fn_args, **fn_kwargs):
            args_str = _pretty_sig(fn, fn_args, fn_kwargs)
            if not args_str:
                args_str = '<no args>'
            retval = fn(*fn_args, **fn_kwargs)
            pretty = _pretty_retval(retval, types=types)
            print(colors.green(f'{identifier}({args_str}) → {pretty}'))
            return retval
        
        return decorator
    
    if _fn is None:
        return wrapper
    return wrapper(_fn)


def logonreturn(*variables):
    def wrapper(fn):
        identifier = fn.__qualname__
        
        @functools.wraps(fn)
        def decorator(*fn_args, **fn_kwargs):
            retval = fn(*fn_args, **fn_kwargs)
            return retval
        
        return decorator
    
    return wrapper


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
    
    def printarg(_name, _val):
        apply(f'{_name} ({type(_val)}):', _val)
    
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
                continue
            printarg(name, val)
    for name, val in kwargs.items():
        printarg(name, val)


def investigate(*,
                args=True,
                ret_val=True,
                print_exc=True,
                locals_on_return=False,
                formatter: Callable = loggr.pformat,
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
                args_str = _pretty_sig(fn, fn_args, fn_kwargs)
                if not args_str:
                    args_str = 'no args'
                print(colors.green(f'entered {identifier}({args_str})', 'bold'))
            else:
                print(colors.green(f'entered {identifier}()', 'bold'))
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
                    print(colors.green(f'{identifier}() returning → {pretty}'))
                
                else:
                    print(colors.green(f'exiting {identifier}()', 'bold'))
                
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
