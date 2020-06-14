import re
import sys
from pprint import pformat as prettyformat
from typing import Callable, Any

import logbook
from logbook import Logger, NOTSET
from more_termcolor import colors
import os

OBJECT_RE = re.compile(r'<(?:[\w\d]+\.)*([\w\d]+) object at (0x[\w\d]{12})>')
TYPE_RE = re.compile(r'(?:<\w+ )([^>]+)')


def _pretty_obj(match) -> str:
    groups = match.groups()
    return f'{groups[0]} ({groups[1]})'


def pformat(obj) -> str:
    if isinstance(obj, dict):
        return prettyformat(obj)
    if isinstance(obj, str) and ' ' not in obj and not obj.endswith(':'):
        string = repr(obj)
    elif isinstance(obj, type):
        string = re.search(TYPE_RE, str(obj)).groups()[0]
    
    else:
        string = str(obj)
    string = re.sub(OBJECT_RE, _pretty_obj, string)
    return string


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
