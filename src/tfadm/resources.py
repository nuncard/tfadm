from .exceptions import Error, PatternError
from .methods import Method, Methods
from .module import Module
from .path import VirtualPath
from .properties import Properties
from .settings import merge, Descriptor, Settings
from .template import jinja, Template
from click import secho
from collections.abc import Mapping
from os import chdir
from os.path import dirname, join as joinpath
from pathlib import Path
import errno

class Resource(Settings):
  address = Descriptor('address')
  conflits_with = Descriptor('conflits_with')
  depends_on = Descriptor('depends_on')
  description = Descriptor('description')
  events = Descriptor('events')
  extends = Descriptor('extends')
  methods = Descriptor('methods')
  module = Descriptor('module')
  path = Descriptor('path')
  properties = Descriptor('properties')
  root = Descriptor('root')
  source = Descriptor('source')
  template = Descriptor('template')

  def __init__(self, owner, name:str, cfg:Mapping, parent=None):
    super().__init__()
    self.owner = owner
    self.parent = parent
    self.name = name

    depends_on = cfg.get('depends_on', [])

    if isinstance(depends_on, str):
      depends_on = [depends_on]

    self.depends_on = depends_on

    self.description = cfg.get('description', '')
    self.path = VirtualPath(self, cfg, 'path')
    self.root = ''
    self.source = cfg.get('source', 'locals.tf.json')
    self.address = cfg.get('address', 'locals')
    self.conflits_with = cfg.get('conflits_with')

    self.template = Template(self, cfg, 'template')
    self.properties = Properties(self, cfg, 'properties')
    self.methods = Methods(self, cfg, 'methods')
    self.events = cfg.get('events', {})
    self.module = Module(self, cfg, 'module')

    self._inherit()

  def __call__(self, command:str, *args, **kwds):
    return self.methods(command, *args, **kwds)

  def _inherit(self):
    parent = self.parent

    self.path._inherit()
    self.properties._inherit()
    self.methods._inherit()
    self.module._inherit()

    if parent:
      self.source = joinpath(dirname(parent.source), self.source)

    self.root = dirname(self.module.file if self.module.file and self.module.file.endswith('.tf.json') else self.source)
    state = None

    while parent and parent.root == self.root:
      state = parent.state
      parent = parent.parent

    if state is None:
      state = Settings()

    self.state = state

  def format(self, key, args, default=None):
    try:
      return super().format(key, args, default)
    except KeyError as e:
      raise PatternError(self.name, *e.args)
    except ValueError as e:
      raise Error(self.name, str(e))

  def trigger(self, event:str, args:Mapping, **options):
    event = 'on' + event
    props = self.properties

    for cmd_name, resources in self.events.get(event, {}).items():
      for resource_name, settings in resources.items():
        _ = Settings(args, clone=True)

        if not isinstance(settings, list):
          settings = [settings]

        for item in settings:
          condition = item.get('when')

          if condition and not jinja.compile_expression(condition)(**args):
            continue

          unset = item.get('unset', [])

          for key in unset:
            if isinstance(key, str):
              _.pop(key)
              continue

            condition = key.get('when')

            if not condition or jinja.compile_expression(condition)(**args):
              _.pop(key.get('key'))

          if resource_name.startswith('.'):
            _.merge(item.get('args'))
          else:
            _ = merge(props.heritage(_), item.get('args'))

          method = self.owner.load(resource_name).methods.get(cmd_name)

          if not isinstance(method, Method):
            raise Error(self.name + '/events/' + event, 'No command named', cmd_name)

          method(_, **merge({}, options, item.get('options', {})))

class Resources(dict):
  def __init__(self):
    super().__init__()

    root_dir = Path.cwd()
    config_dir = root_dir / ('.' + __package__)

    if not config_dir.is_dir():
      for root_dir in config_dir.parents:
        config_dir = root_dir / config_dir.stem

        if config_dir.is_dir():
          break

    self.paths = []
    name = config_dir.stem

    for parent in config_dir.parents:
      resources = parent / name / 'resources'

      if resources.is_dir():
        self.paths.append(resources)

    if not self.paths:
      raise FileNotFoundError(errno.ENOENT, 'Not a {} project (or any of the parent directories)'.format(__package__), name)

    chdir(root_dir)
    self.root_dir = root_dir

  def each(self, callback, parent=None, *args, **kwds):
    resources = []

    # Get all the the resources at the same level
    for resource in self.values():
      _ = resource.methods['sync'].parent
      _ = resource.parent if _ is None else _.owner

      if _ is parent:
        resources.append(resource)

    # Auxiliar variable to detect if it enters an infinite loop due to bad
    # `depends_on` configuration
    done = []
    count = 0
    skipped = 0

    while resources:
      execute = True
      resource = resources.pop(0)
      depends_on = resource.depends_on

      if depends_on:
        for dependency in depends_on:
          dependency = self.load(dependency)

          if dependency.name == resource.name:
            # Ignore if it depends on it self
            continue

          if dependency.name not in done:
            execute = False
            break

      if execute:
        done.append(resource.name)

        if resource.name.startswith('.'):
          count += self.each(lambda r: callback(r, *args, **kwds), resource)
        else:
          print()
          secho(resource.name.upper(), bold=True)
          print()

          callback(resource, *args, **kwds)
          count += 1

        skipped = 0
      elif skipped < len(resources):
        # Puts the resource back on queue
        resources.append(resource)
        # Increases skipped by one in order to stop the cycle if unable to
        # resolve all dependencies
        skipped += 1
      else:
        # Raise error in case of bad configuration
        raise Error(resource.name + '/depends_on', str(depends_on))

    return count

  def extendConfig(self, cfg:Mapping, current=None):
    extends = cfg.pop('extends', None)

    if extends:
      if not isinstance(extends, list):
        extends = [extends]

      for name in extends:
        file, _ = self.loadConfig(name, current)
        cfg = self.extendConfig(merge(_, cfg, extend=True, clone=False), file)

    return cfg

  def load(self, name:str):
    if name is None:
      return None

    file = Path(name)

    if file.suffix in ['.yml', '.yaml']:
      name = file.stem

    resource = self.get(name)

    if resource is not None:
      return resource

    file, cfg = self.loadConfig(name)
    cfg = self.extendConfig(cfg, file)

    self[name] = resource = Resource(self, name, cfg, self.load(cfg.pop('parent', None)))

    return resource

  def loadAll(self):
    for file in self.paths[0].iterdir():
      if file.suffix in ['.yml', '.yaml'] and not file.name.startswith('.'):
        self.load(file.name)

    return self

  def loadConfig(self, name:str, current=None) -> list:
    for path in self.paths:
      file = path / name

      if file.suffix not in ['.yml', '.yaml']:
        file = file.with_suffix(file.suffix + '.yml')

        if not file.is_file():
          file = file.with_suffix('.yaml')

      if file.is_file() and file != current:
        return [file, Resource.load(file)]

    raise FileNotFoundError(errno.ENOENT, 'No such file', (self.paths[0] / file.with_suffix('.yml').stem).relative_to(self.root_dir).__str__())