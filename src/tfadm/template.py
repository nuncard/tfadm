from .settings import get, Settings, Descriptor
from collections.abc import Mapping
from jinja2 import Environment

jinja = Environment()

class Template(Settings):
  template = Descriptor('data')
  fields = Descriptor('fields')

  def __init__(self, owner, cfg:Mapping, key:str):
    super().__init__(get(cfg, key))
    self.owner = owner
    self.key = key
    self.setdefault('data', {})
    self.setdefault('fields', [])

  def __call__(self, args:Mapping):
    values = {}

    for key in self.fields:
      values[key] = self.format('data/' + key, args)

    return Settings(self.template, clone=True, extend=False).update(values)

  def format(self, key:str, args:Mapping):
    return self.owner.format(self.key + '/' + key, args)
