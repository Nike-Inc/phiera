import re
import os
import logging
from copy import deepcopy

from .exceptions import InterpolationError
from .backends import YAMLBackend, SopsYAMLBackend, JSONBackend
from .util import LookupDict, sym_lookup

function = re.compile(r'''%\{(scope|hiera|lookup|literal|alias)\(['"](?:::|)([^"']*)["']\)\}''')
interpolate = re.compile(r'''%\{(?:::|)([^\}]*)\}''')
rformat = re.compile(r'''%{(?:::|)([a-zA-Z_-|\d]+)}''')

LOGGER = logging.getLogger(__name__)

class Merge(object):
    def __init__(self, typ, deep=False):
        self.typ = typ
        self.deep = deep

        if typ == dict:
            self.value = LookupDict()
        else:
            self.value = typ()

    def merge_value(self, value):
        if isinstance(self.value, list):
            self.value += list(value)
        elif isinstance(self.value, set):
            self.value = self.value | set(value)
        elif isinstance(self.value, dict):
            if self.deep:
                self.value = self.deep_merge(self.value, value)
            else:
                for k, v in value.items():
                    if k not in self.value:
                      self.value[k] = v
        elif isinstance(self.value, str):
          self.value = value
        else:
            raise TypeError("Cannot handle merge_value of type %s", type(self.value))

    def deep_merge(self, a, b):
        '''recursively merges dicts. not just simple a['key'] = b['key'], if
        both a and bhave a key who's value is a dict then dict_merge is called
        on both values and the result stored in the returned dictionary.'''
        if not isinstance(b, dict):
            return b
        result = deepcopy(a)
        for k, v in b.items():
            if k in result and isinstance(result[k], dict):
                    result[k] = self.deep_merge(result[k], v)
            elif k in result and isinstance(result[k], list):
                if isinstance(v, list):
                    v = [_ for _ in v if _ not in result[k]]
                    result[k] += deepcopy(v)
                else:
                    result[k].append(v)
            else:
                result[k] = deepcopy(v)
        return result

class ScopedHiera(object):
    def __init__(self, hiera, context={}):
        self.hiera = hiera
        self.context = context

    def has(self, key, **kwargs):
        kwargs.update(self.context)
        return self.hiera.has(key, **kwargs)

    def get(self, key, default=None, merge=None, merge_deep=False, throw=False, context={}, **kwargs):
        new_context = {}
        new_context.update(self.context)
        new_context.update(context)
        new_context.update(kwargs)
        return self.hiera.get(key, default, merge, merge_deep, throw, new_context)

    def __getattr__(self, name):
        if hasattr(self.hiera, name):
            return getattr(self.hiera, name)
        raise AttributeError


class Hiera(object):
    """
    The Hiera object represents a first-class interaction between Python and
    Hiera data. It takes a base-hiera config YAML file, and exposes methods
    to retrieve and fully resolve Hiera data.

    # XXX fix doc, this can be a dict
    :param base_config: The Hiera base configuration: file path, file-like object, or dict
    :param backends: A list of backends to use for loading, by default this is
        YAMLBackend, SopsYAMLBackend and JSONBackend
    :param context: Any dictionary of format/context variables to default for the
        liftime of this instance.
    :param kwargs: Any additional kwargs will be added to the context
    """
    def __init__(self, base_config, backends=None, base_path=None, context={}, **kwargs):
        self.base_config = base_config
        self.context = context
        self.context.update(kwargs)

        self.cache = {}
        self.paths = []

        self.load(backends or [YAMLBackend, SopsYAMLBackend, JSONBackend])

    def load(self, backends, base_path=None):
        """
        This function loads the base Hiera configuration, attempting to parse and
        build state based on it. This will raise exceptions if the loading process
        fails due to invalid configuration.
        """

        # If we don't have a file-like object, attempt to open as a file path
        if type(self.base_config) is dict:
            self.base = self.base_config
            if base_path is None:
                self.base_path = os.getcwd()
            else:
                self.base_path = base_path
        else:
            if not hasattr(self.base_config, 'read'):
                self.base_path = os.path.dirname(self.base_config)
                self.base_config = open(self.base_config)
            else:
                self.base_path = os.getcwd()

            # Load our base YAML configuration
            self.base = YAMLBackend.load_ordered(self.base_config)

        if not self.base:
            raise Exception("Failed to parse base Hiera configuration")

        # Load all backends
        self.backends = {}

        for backend in sym_lookup(self.base, 'backends'):
            obj = [i for i in backends if i.NAME == backend]
            if not len(obj):
                raise Exception("Invalid Backend: `{}`".format(backend))
            self.backends[backend] = obj[0](self, sym_lookup(self.base, backend))

        # Make sure we have at least a single backend
        if not len(self.backends):
            raise Exception("No backends could be loaded")

        hierarchy = sym_lookup(self.base, 'hierarchy')
        if hierarchy is None:
            raise Exception("Invalid Base Hiera Config: missing hierarchy key")

        self.hierarchy = []

        # Load our heirarchy
        for path in hierarchy:
            self.hierarchy.append(rformat.sub("{\g<1>}", path, count=0))

        # Load our backends
        for backend in list(self.backends.values()):
            backend.datadir = rformat.sub("{\g<1>}", backend.datadir, count=0)

        # Now pre-load/cache a bunch of global stuff. If context vars where provided
        #  in the constructor, we'll also load those files into the cache.
        self.get(None)

    def load_directory(self, path, backend=None):
        """
        Walks an entire directory and attempts to load all relevant data files
        based on our backends. Optionally can only load for one backend.
        """
        for root, dirs, files in os.walk(path):
            for f in files:
                backend = backend or self.backends.get(':{}'.format(os.path.splitext(f)[-1]))
                if backend:
                    yield self.load_file(os.path.join(root, f), backend)

    def load_file(self, path, backend, ignore_cache=False):
        """
        Attempts to load a file for a specific backend, caching the result.
        """
        if path not in self.cache or ignore_cache:
            try:
                self.cache[path] = backend.load(backend.read_file(path))
            except Exception as e:
                raise Exception("Failed to load file {}: `{}`".format(path, e))
        return path

    def can_resolve(self, s):
        """
        Returns true if any resolving or interpolation can be done on the provided
        string
        """
        if (isinstance(s, str) or isinstance(s, str)) and (function.findall(s) or interpolate.findall(s)):
            return True
        return False

    def resolve_function(self, s, paths, context, merge):
        """
        Attempts to fully resolve a hiera function call within a value. This includes
        interpolation for relevant calls.
        """
        calls = function.findall(s)
        # If this is an alias, just replace it (doesn't require interpolation)
        if len(calls) == 1 and calls[0][0] == 'alias':
            if function.sub("", s) != "":
                raise Exception("Alias can not be used for string interpolation: `{}`".format(s))
            try:
              value = self.get_key(calls[0][1], paths, context, merge)
              return value
            except KeyError as e:
              raise InterpolationError("Alias lookup failed: key '{}' does not exist".format(calls[0][1]))

        # Iterate over all function calls and string interpolate their resolved values
        for call, arg in calls:
            if call == 'hiera' or call == 'lookup':
                replace = self.get_key(arg, paths, context, merge)
            elif call == 'scope':
                replace = context.get(arg)
            elif call == 'literal':
                replace = arg
            elif call == 'alias':
                raise Exception("Invalid alias function call: `{}`".format(s))

            if not replace:
                raise Exception("Could not resolve value for function call: `{}`".format(s))

            if isinstance(replace, str):
                # Replace only the current function call with our resolved value
                s = function.sub(replace, s, 1)
            elif call == 'scope':
                s = replace
            else:
                raise Exception("Resolved value is not a string for function call: `{}`".format(s))


        return s

    def resolve_interpolates(self, s, context):
        """
        Attempts to resolve context-based string interpolation
        """
        interps = interpolate.findall(s)

        for i in interps:
            # XXX - should this throw an error, interpolate to an empty string, or be configurable?
            # what does ruby hiera do?
            s = interpolate.sub((context.get(i) or ''), s, 1)

        return s

    def resolve(self, s, paths, context, merge):
        """
        Fully resolves an object, including function and interpolation based resolving.
        """
        if isinstance(s, dict):
            return self.resolve_dict(s, paths, context, merge)
        elif isinstance(s, list):
            return list(self.resolve_list(s, paths, context, merge))
        elif not self.can_resolve(s):
            return s

        base = self.resolve_function(s, paths, context, merge)

        # If we can string interpolate the result, lets do that
        if isinstance(base, str):
            base = self.resolve_interpolates(base, context)

        return base

    def resolve_dict(self, obj, paths, context, merge):
        """
        Recursively and completely resolves all Hiera interoplates/functions
        within a dictionary.
        """
        new_obj = LookupDict()
        for k, v in obj.items():
            new_obj[k] = self.resolve(v, paths, context, merge)
        return new_obj

    def resolve_list(self, obj, paths, context, merge):
        for item in obj:
            yield self.resolve(item, paths, context, merge)

    def get_key(self, key, paths, context, merge):
        """
        Get the value of a key within hiera, resolving if required
        """
        merges = {}
        for path in paths:
            if self.cache[path] is not None and key is not None:
                cache = None
                try:
                  cache = self.cache[path].lookup(key)
                except KeyError as e:
                  pass

                if cache is not None:
                  if merge and not key in merges:
                      merges[key] = Merge(merge.typ, merge.deep)

                  value = self.resolve(cache, paths, context, (merges[key] if merge and merge.deep else merge))

                  if merge and merges[key]:
                      merges[key].merge_value(value)
                  else:
                      return value

        if merge and key in merges and merges[key].value is not None:
            return merges[key].value
        else:
            if key!= None and len(key.split('.')) > 1:
                LOGGER.error("Lookup key: '{}' not found. Make sure you are providing this key in YAML configuration.".format(key))
            raise KeyError(key)

    def scoped(self, context={}, **kwargs):
        context.update(kwargs)
        return ScopedHiera(self, context)

    def has(self, key, **kwargs):
        """
        Returns true if the key exists in hiera, false otherwise
        """
        try:
            self.get(key, throw=True, **kwargs)
            return True
        except KeyError:
            return False

    def get(self, key, default=None, merge=None, merge_deep=False, throw=False, context={}, **kwargs):
        """
        Attempts to retrieve a hiera variable by fully resolving its location.

        :param key: They Hiera key to retrieve
        :param default: If the Hiera key is not found, return this value
        :param merge: If set to a list or dictionary, will perform a array or hash
            merge accordingly.
        :param throw: If true, will ignore default and throw KeyError on a missing
            key.
        :param context: A dictionary of key-value pairs to be passed in as context
            variables.
        :param kwargs: Any kwargs passed will override context-variables.
        """
        new_context = {}
        new_context.update(self.context)
        new_context.update(context)
        new_context.update(kwargs)

        # Filter None values
        new_context = {k: v for k, v in list(new_context.items()) if v}

        # First, we need to resolve a list of valid paths, in order and load them
        paths = []

        for backend in list(self.backends.values()):
            for path in self.hierarchy:
                try:
                    path = os.path.join(
                        self.base_path,
                        backend.datadir.format(**new_context),
                        path.format(**new_context))
                except KeyError:
                    continue
                if os.path.isdir(path):
                    paths += list(self.load_directory(path, backend))
                elif os.path.exists(path + '.' + backend.NAME):
                    paths.append(self.load_file(path + '.' + backend.NAME, backend))

        if merge:
            merge = Merge(merge, merge_deep)

        # Locate the value, or fail and return the defaults
        try:
            return self.get_key(key, paths, new_context, merge=merge)
        except KeyError:
            if throw:
                raise
            return default
