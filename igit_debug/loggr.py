import re
import sys
from pprint import pformat as prettyformat
from typing import Callable, Any

import logbook
from logbook import Logger, NOTSET
from more_termcolor import colors
import os

OBJECT_RE = re.compile(r'<(?:[\w\d]+\.)*([\w\d]+) object at (0x[\w\d]{12})>')

# "<class 'int'>" → "int"
TYPE_RE = re.compile(r'<\w+ [\'"]([^\"\']+)')


def _pretty_obj(match) -> str:
    groups = match.groups()
    return f'{groups[0]} ({groups[1]})'


def pformat(obj, *, types=False) -> str:
    def _type_pformat(_obj: type) -> str:
        _s = str(_obj)
        _match = TYPE_RE.search(_s)
        _groups = _match.groups()
        return _groups[0]
    
    def _generic_pformat(_obj, _types: bool) -> str:
        if not _types:
            _string = f'{_obj}'
        else:
            _type_repr = f"({_type_pformat(type(_obj))})"
            _string = f'{_obj} {colors.dark(_type_repr)}'
        return _string
    
    if isinstance(obj, dict):
        return prettyformat(obj)
    isstr = isinstance(obj, str)
    if isstr and ' ' not in obj and not obj.endswith(':'):
        string = repr(obj)
    elif isinstance(obj, type):
        string = _type_pformat(obj)
    elif not isstr and hasattr(obj, '__iter__'):
        # reaching here means it's not str nor dict
        objlen = 0
        
        for item in obj:  # use generic pformat if collection is too long or any of its items is a collection
            if objlen > 6:
                string = _generic_pformat(obj, types)
                break
            if hasattr(item, '__iter__') and not isinstance(item, str):
                string = _generic_pformat(obj, types)
                break
            objlen += 1
        else:
            formatted_items = []
            for item in obj:
                formatted_item = pformat(item, types=types)
                formatted_items.append(formatted_item)
            
            formatted_obj = type(obj)(formatted_items)
            string = str(formatted_obj)
    
    else:
        string = _generic_pformat(obj, types)
    string = re.sub(OBJECT_RE, _pretty_obj, string)
    return string.encode('utf-8').decode('unicode_escape')


def fmt_arg(arg) -> str:
    string = pformat(arg)
    
    if string.endswith(':'):
        return colors.ul(string[:-1]) + ': '
    else:
        return string + ', '


def fmt_args(args) -> str:
    formatted_args = [fmt_arg(a) for a in args]
    sumlen = sum(map(len, formatted_args))
    if len(args) > 1:
        if sumlen <= 80:
            joined = ''.join(formatted_args).strip()
        
        else:
            joined = '\n\t' + '\n\t'.join(formatted_args).strip()
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
        verbose = os.getenv('IGIT_VERBOSE', False)
        if kwargs.get('only_verbose'):
            if not verbose:
                return
            kwargs.pop('only_verbose')
        
        if selfarg.only_verbose and not verbose:
            return
        msg = fmt_args(args)
        if (frame_correction := kwargs.get('frame_correction')) is None:
            kwargs['frame_correction'] = 2
        else:
            kwargs['frame_correction'] = int(frame_correction) + 2
        return fn(selfarg, msg, **kwargs)
    
    return logwrap


class Loggr(Logger):
    
    def __init__(self, name=None, level=NOTSET, *, only_verbose=False):
        super().__init__(name, level)
        self.only_verbose = only_verbose
    
    @log_preprocess
    def debug(self, msg, **kwargs):
        super().info(colors.brightwhite(msg), **kwargs)
    
    @log_preprocess
    def info(self, msg, **kwargs):
        super().info(colors.green(msg), **kwargs)
    
    @log_preprocess
    def warn(self, msg, **kwargs):
        super().warn(colors.yellow(msg), **kwargs)
    
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
        super().info(colors.green(msg, 'bold'), **kwargs)


logbook.StreamHandler(sys.stdout, format_string='{record.time:%T.%f} | {record.module}.{record.func_name}() | {record.message}').push_application()
