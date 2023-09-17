from . import Command
from ...settings import get, Descriptor
from collections.abc import Mapping
from json import loads as loadjson
from subprocess import check_output

class Show(Command):
  resources = Descriptor('resources')

  def __init__(self, owner, cfg:Mapping, key:str):
    super().__init__(owner, cfg, key + '/show')

  def __call__(self, *args) -> Mapping:
    this = super().__call__('-json', '-no-color', *args)
    state = get(loadjson(check_output(this)), self.resources, [])
    return self.owner.state.update({self.cwd: state})

  def _inherit(self):
    super()._inherit()

    if self.resources is None:
      address = ['values/root_module']

      resource = self.owner
      parent = resource.parent

      while parent and resource.module and resource.module.file.endswith('.tf.json'):
        address.append('child_modules')
        resource = parent
        parent = resource.parent

      address.append('resources/address')
      self.resources = '/'.join(address)
