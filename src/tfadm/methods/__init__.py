from ..exceptions import Error
from ..settings import get, Settings
from click import secho
from collections.abc import Mapping
from pathlib import PurePosixPath
from shlex import join as joincmd

class Method(Settings):
  def __init__(self, owner, cfg:Mapping, key:str):
    super().__init__(get(cfg, key))
    self.owner = owner
    self.key = PurePosixPath(key)
    self.context = PurePosixPath(owner.name, self.key)

  def _inherit(self):
    parent = self.owner.parent

    if parent:
      parent = parent.get(str(self.key))

    self.parent = parent

  def format(self, key:str, args:Mapping):
    return self.owner.format(str(self.key / key), args)

class Group(Method):
  def __init__(self, owner, cfg:Mapping, key:str, methods:list):
    super().__init__(owner, cfg, key)

    for method in methods:
      method = method(owner, cfg, key)
      self[method.key.name] = method

  def __call__(self, command:str, *args, **kwds):
    method = self.get(command)

    if not isinstance(method, Method):
      raise Error(self.owner.name + '/' + str(self.key) + '()', 'No command named', command)

    return method(*args, **kwds)

  def _inherit(self):
    for method in self.values():
      method._inherit()

class Methods(Group):
  def __init__(self, owner, cfg:Mapping, key:str):
    from .sync import Sync
    from .terraform import Terraform
    from .update import Create, Update

    super().__init__(owner, cfg, key, [
      Create,
      Sync,
      Terraform,
      Update,
    ])

class ExternalCommand(Method):
  def __call__(self, *args) -> list:
    this = self.args(*args)
    secho('$ {}'.format(joincmd(this)), bold=True)
    return this

  def __str__(self):
    return joincmd(self.args())

  def args(self, *args) -> list:
    return args
