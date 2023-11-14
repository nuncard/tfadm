from .settings import get, update
from collections import UserList
from collections.abc import Mapping
from parse import parse
from pathlib import Path, PurePosixPath
import re

class VirtualPath(UserList):
  def __init__(self, owner, cfg:Mapping, key:str):
    super().__init__()
    self.owner = owner
    self.key = key
    path = cfg.get(key, [])

    if isinstance(path, str):
      path = PurePosixPath(path).parts

    self.extend(path)

  def __call__(self, path:str) -> dict:
    this = self.__str__()
    resource = self.owner
    path = Path(path)

    if not resource.source.startswith(this) and path.is_dir():
      source = PurePosixPath(self.owner.source)
      mapping = parse(self.join(*source.parts[0:len(path.parts)]), self.join(*path.parts), case_sensitive=True)
      args = mapping.named if mapping else {}
      return args

    parts = path.parts

    mapping = {}
    last = len(self.data) - 1

    for i in range(len(parts)):
      if i >= last:
        mapping[self[i]] = self.join(*parts[i:])
        break
      mapping[self[i]] = parts[i]

    return update({}, mapping)

  def __str__(self) -> str:
    parts = []
    pattern = re.compile('/([^/]+)')

    for key in self.data:
      parts.append(pattern.sub(r'[\1]', key))

    return '{' + '}/{'.join(parts) + '}'

  def _inherit(self):
    parent = self.owner.parent

    if parent and parent.path:
      inherited = [*parent.path]

      def inherit(key, prop):
        if key in parent.path and not prop.get('inherit', True):
          inherited.remove(key)

      parent.properties.walk(inherit)

      if inherited:
        inherited.extend(self.data)
        self.data = inherited

    self.parent = parent

  def args(self, args:Mapping):
    this = {}

    for key in self.data:
      value = get(args, key)

      if value is not None:
        this[key] = value

    return this

  def extend(self, *others):
    for other in others:
      super().extend(other)
    return self

  def format_map(self, args):
    parts = []
    err = None

    for key in self.data:
      value = get(args, key)

      if value is None:
        err = KeyError(key)
      elif err is None:
        parts.append(value)
      else:
        raise err

    return self.join(*parts)

  @staticmethod
  def join(*parts:str):
    return '/'.join(parts)

  def parts(self, args:Mapping) -> list:
    parts = []

    for key in self.data:
      value = get(args, key)

      if value is None:
        break

      parts.append(value)

    return parts
