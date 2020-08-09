import re
from pprint import pformat as prettyformat

from more_termcolor import colors

from igit_debug.util import safeiter

OBJECT_RE = re.compile(r'<(?:[\w\d]+\.)*([\w\d]+) object at (0x[\w\d]{12})>')
TYPE_RE = re.compile(r'<\w+ [\'"]([^\"\']+)')


# "<class 'int'>" → "int"

def _pretty_obj(match) -> str:
    groups = match.groups()
    return f'{groups[0]} ({groups[1]})'


def pformat(obj, *,
            types=False,
            depth=1,
            stringifier=repr
            ) -> str:
    """
    :param obj: The object to pretty-print. Can be (almost) anything.
    :param bool types: Specifiy True to the object's type alongside its value.
    :param int depth: For recursive collections, how deep should the function apply itself to sub items.
    :param Callable stringifier: function to convert a primitive to string
    :param bool colorize: whether to use colors in the output string.
    """
    
    def _type_pformat(_obj: type) -> str:
        _s = str(_obj)
        _match = TYPE_RE.search(_s)
        _groups = _match.groups()
        return _groups[0]
    
    def _generic_pformat(_obj, *, _types: bool, _stringifier=str) -> str:
        if not _types:
            _string = _stringifier(_obj)
        else:
            _type_repr = f"({_type_pformat(type(_obj))})"
            _string = f'{_stringifier(_obj)} {colors.dark(_type_repr)}'
        return _string
    
    def _recursive_pformat(_obj, *, _types: bool, _depth: int) -> str:
        if not _types:
            return prettyformat(_obj, depth=_depth)
        
        _formatted_items = []
        for _item in _obj:
            _formatted_item = pformat(_item, types=_types, depth=_depth, stringifier=str)
            _formatted_items.append(_formatted_item)
        
        _formatted_obj = type(_obj)(_formatted_items)
        
        _string = str(_formatted_obj)
        return _string
    
    if isinstance(obj, dict):
        return prettyformat(obj, depth=depth)
    isstr = isinstance(obj, str)
    if isstr and ' ' not in obj and not obj.endswith(':'):
        # string = stringifier(obj)
        string = _generic_pformat(obj, _types=types, _stringifier=stringifier)
    elif isinstance(obj, type):
        string = _type_pformat(obj)
    elif not isstr and (iterator := safeiter(obj)):
        # reaching here means it's not str nor dict nor a class constructor
        if depth:
            depth = max(0, depth - 1)
            if depth == 0:
                depth = None
            string = _recursive_pformat(obj, _types=types, _depth=depth)
        else:
            string = _generic_pformat(obj, _types=types)
        # for item in iterator:
        #     # use generic pformat if collection is too long
        #     # or any of its items is a collection
        #     if objlen > 6:
        #         string = _generic_pformat(obj, types)
        #         break
        #     if not isinstance(item, str) and safeiter(item):
        #         string = _generic_pformat(obj, types)
        #         break
        #     objlen += 1
        # else:
        #     string = _recursive_pformat(obj, types)
    
    else:
        string = _generic_pformat(obj, _types=types)
    string = re.sub(OBJECT_RE, _pretty_obj, string)
    return string.encode('utf-8').decode('unicode_escape')
