from . import Command
from collections.abc import Mapping
from subprocess import check_call

class Init(Command):
  def __init__(self, owner, cfg:Mapping, key:str):
    super().__init__(owner, cfg, key + '/init')

  def __call__(self, *args) -> bool:
    this = super().__call__('-input=false', *args)
    check_call(this)
    return self.owner.state.update({str(self.cwd): {}})
