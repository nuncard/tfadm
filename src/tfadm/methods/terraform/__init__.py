from .. import ExternalCommand, Group
from collections.abc import Mapping

class Command(ExternalCommand):
  def __call__(self, *args) -> list:
    return super().__call__(*args)

  def args(self, *args) -> list:
    this = ['terraform']

    if self.cwd:
      this.append('-chdir=' + self.cwd)

    this.append(self.key.name)
    this.extend(args)

    return this

  @classmethod
  def chdir(cls, path):
    cls.cwd = path
    return path

class Terraform(Group):
  def __init__(self, owner, cfg:Mapping, key:str):
    from .import_ import Import
    from .init import Init
    from .show import Show

    super().__init__(owner, cfg, key + '/terraform', [
      Import,
      Init,
      Show,
    ])

  def __call__(self, command:str, *args, **kwds):
    if command == 'chdir':
      return Command.chdir(*args, **kwds)

    return super().__call__(command, *args, **kwds)
