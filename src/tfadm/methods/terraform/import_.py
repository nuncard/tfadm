from . import Command
from ...settings import pprint, Descriptor
from collections.abc import Mapping
from shlex import join as joincmd
from subprocess import check_call

class Import(Command):
  address = Descriptor('address')
  id = Descriptor('id')

  def __init__(self, owner, cfg:Mapping, key:str):
    super().__init__(owner, cfg, key + '/import')

  def __call__(self, args:Mapping) -> str:
    if not self.id:
      return None

    context = str(self.context) + '()'

    try:
      address = self.format('address', args)
      id = self.format('id', args)
    except Exception as err:
      pprint({self.context: {'args': args}})
      raise err

    state = self.owner.state.get(self.cwd)

    if address in state:
      print(context + ':', 'Already managing a remote object for', address)
    else:
      this = super().__call__('-input=false', address, id)
      check_call(this)
      state.append(address)

    return id

  def __str__(self):
    this = super().args()
    this.extend(['-input=false', '{address}', '{id}'])
    return joincmd(this)

  def _inherit(self):
    super()._inherit()

    resource = self.owner
    address = self.address

    if address is None and resource.address.startswith('resource/'):
      address = '/'.join(resource.address.split('/')[1:3])
      address = address.replace('/', '.')

    if address:
      address = [address]

      parent = resource.parent

      while parent and resource.module and resource.module.file.endswith('.tf.json'):
        address.extend([resource.module.name, 'module'])
        resource = parent
        parent = resource.parent

      address = '.'.join(reversed(address))

    self.address = address
