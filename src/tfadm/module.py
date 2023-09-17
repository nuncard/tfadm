from .settings import get, Settings, Descriptor
from .template import Template
from os.path import dirname, join as joinpath
from pathlib import Path, PurePosixPath
from collections.abc import Mapping
from json import dumps as tojson
import hashlib

class Module(Settings):
  args = Descriptor('args', [])
  file = Descriptor('file')
  name = Descriptor('name')
  source = Descriptor('source')
  template = Descriptor('template')

  def __init__(self, owner, cfg:Mapping, key:str):
    super().__init__(get(cfg, key))
    self.owner = owner
    self.key = PurePosixPath(key)

    if self.file:
      self.template = Template(self, self.data, 'template')
      source = self.source

      if source is None:
        self.source = joinpath('.', dirname(owner.source))
      elif not source.startswith('./'):
        self.source = joinpath('.', self.source)

  def __call__(self, args:Mapping) -> list:
    name = self.format('name', args)

    if name is None:
      name = tojson(self.owner.properties.primarykey(args, sort_keys=True))
      name = 'mod-' + hashlib.new('md5', name.encode()).hexdigest()

    instance = Settings({'source': self.format('source', args)})

    for key in self.args:
      instance.update({key: get(args, key)})

    instance.merge(self.template(args))

    return ['module/' + name, instance]

  def _inherit(self):
    parent = self.owner.parent
    self.parent = parent.module if parent else parent
    file = self.file

    if file and parent:
      psource = Path(parent.source)

      if file.endswith('.tf.json'):
        self.file = psource.parent.joinpath(file)
      else:
        self.source = joinpath('.', psource.parent.joinpath(self.source))

  def format(self, key:str, args:Mapping):
    return self.owner.format(str(self.key / key), args)
