from collections import OrderedDict
from functools import reduce

def sym_lookup(obj, key, default=None):
    """
    dict lookup w/ optional ruby-symbol-like keys
    """
    for lookup_key in [ key, ':{}'.format(key) ]:
        if lookup_key in obj:
            return obj[lookup_key]

    return default

class LookupDict(OrderedDict):

  def lookup(self, key):
      return reduce(lambda obj, key: obj[int(key) if type(obj) is list else key], key.split('.'), self)

  def __hash__(self):
      return hash(frozenset(self))
