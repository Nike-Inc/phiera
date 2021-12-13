import yaml, json
import subprocess

from .util import LookupDict
from .util import sym_lookup

class Backend(object):
    """
    Backends provide a way of loading data from files. They should
    override .load with a custom loading method.
    """
    NAME = None

    def __init__(self, parent, obj=None):
        self.parent = parent

        self.obj = obj or {}
        self.datadir = sym_lookup(self.obj, "datadir", "/etc/puppetlabs/code/environments/%{environment}/hieradata")

    def read_file(self, path):
      return open(path).read()

    def load(self, data):
        raise NotImplementedError("Subclasses must implement .load")

class YAMLBackend(Backend):
    NAME = 'yaml'

    def load(self, data):
        return self.load_ordered(data)

    @staticmethod
    def load_ordered(stream, Loader=yaml.Loader, object_pairs_hook=LookupDict):
        class OrderedLoader(Loader):
            pass

        def construct_mapping(loader, node):
            loader.flatten_mapping(node)
            return object_pairs_hook(loader.construct_pairs(node))

        OrderedLoader.add_constructor(
                yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG,
                construct_mapping)
        return yaml.load(stream, OrderedLoader)

class SopsYAMLBackend(YAMLBackend):
    NAME = 'yaml.enc'

    def read_file(self, path):
      return subprocess.check_output(['sops', '--input-type=yaml', '--output-type=yaml', '-d', path])

class JSONBackend(Backend):
    NAME = 'json'

    def load(self, data):
        return json.loads(data, object_pairs_hook=LookupDict)
