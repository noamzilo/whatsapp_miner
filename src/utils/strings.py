import re
from typing import Dict


def template_substitution(template_string: str, values: Dict[str, str],
                          keep_missing_keys=False, key_marker: str = '$') -> str:
    """
    Substitutes all instances of keys defined in the given `values` dictionary with its value.

    It is different from python-native template substitution because it supports custom key markers,
    supports "dollar-sandwich" notation (e.g. $KEY$) and well as native notation ($K) and supports custom
    treatment of missing keys.

    If keepMissingKeys is true and some key is missing from the map, reference to it will be left as is,
    otherwise it will be removed.
    Examples:
        templateString = "$KEY1$ $KEY2$ $NotAKey"
        values = {KEY1: Val1}
        1. keepMissingKeys = true
            Result: Val1 $KEY2$ $NotAKey
        2. keepMissingKeys = false
            Result: Val1  $NotAKey
    """
    if key_marker == '$':
        key_marker = '\\$'

    regexp = re.compile(f"({key_marker}([a-zA-Z0-9\-_]+){key_marker}?)")
    res = template_string
    m = regexp.search(res)
    start = 0
    while m:
        key_name = m[2]
        if not keep_missing_keys or key_name in values:
            res = res.replace(m[1], values.get(key_name, ""))
        else:
            start = m.end()
        m = regexp.search(res, start)

    return res

def str2bool(v):
  return v.lower() in ("yes", "true", "t", "1")