from collections import UserDict
from fnmatch import fnmatchcase
from io import StringIO
from json import dump as dump_json
from sys import stdout
from typing import Any, Sequence, Mapping
from yaml import dump as dump_yaml, load as load_yaml, FullLoader
import re

def format_map(format_spec:Any, args:Mapping) -> Any:
  if isinstance(format_spec, str):
    return format_spec.format_map(args)

  if isinstance(format_spec, Mapping):
    result = {}

    for key, value in format_spec.items():
      try:
        result[key] = format_map(value, args)
      except KeyError as e:
        raise KeyError(key, *e.args)

    return result

  if isinstance(format_spec, Sequence):
    result = []

    for i in range(len(format_spec)):
      try:
        result.append(format_map(format_spec[i], args))
      except KeyError as e:
        raise KeyError(str(i), *e.args)

    return result

  return format_spec

def get(settings:Any, path:str, default:Any = None, flatten:bool = True) -> Any:
  if isinstance(settings, Mapping):
    for key, value in settings.items():
      if key == path:
        return value

      if path.startswith(key + '/'):
        return get(value, path[len(key) + 1:], default, flatten)

    return default

  if isinstance(settings, Sequence) and not isinstance(settings, str):
    try:
      try:
        return settings[int(path)]
      except ValueError:
        pass

      try:
        i = path.index('/')
        return get(settings[int(path[0:i])], path[i + 1:], default, flatten)
      except ValueError:
        pass
    except IndexError:
      return default

    values = []

    for value in settings:
      value = get(value, path, default, flatten)

      if value is not None:
        if flatten and isinstance(value, Sequence) and not isinstance(value, str):
          values.extend(value)
        else:
          values.append(value)

    return values if values else default

  return default

def getformat(settings:Any, path:str, args:Mapping, default:Any = None) -> Any:
  try:
    value = format_map(get(settings, path), args)
    return default if value is None else value
  except KeyError as e:
    raise KeyError(path, *e.args)

def match(settings:Any, patterns:Any, literally:bool = False, default:bool = False) -> bool:
  if settings == patterns:
    return True

  if settings is None:
    return default

  if isinstance(patterns, Mapping):
    for key, pattern in patterns.items():
      if key == '$not':
        if match(settings, pattern, literally, default):
          return False
      else:
        if not isinstance(settings, Mapping):
          return False

        value = get(settings, key)

        if not match(value, pattern, literally, default):
          return False
    
    return True

  if isinstance(patterns, Sequence) and not isinstance(patterns, str):
    for pattern in patterns:
      if match(settings, pattern, literally, default):
        return True

    return False

  if literally:
    return False

  if isinstance(patterns, str) and fnmatchcase(str(settings), patterns):
    return True

  return False

def merge(result:Any, *others, extend:bool = False, clone:bool = True) -> Any:
  for other in others:
    if other is None:
      continue

    if isinstance(other, Mapping):
      if isinstance(result, Mapping):
        for key, value in other.items():
          if value is None:
            result[key] = value
          else:
            result[key] = merge(result.get(key), value, extend=extend, clone=clone)
      elif isinstance(result, Sequence) and not isinstance(result, str):
        try:
          for key, value in other.items():
            i = int(key)
            result[i] = merge(result[i], value, extend=extend, clone=clone)
        except:
          if clone:
            other = merge({}, other)

          if extend:
            result.append(other)
          else:
            result = other
      else:
        result = merge({}, other) if clone else other
    elif isinstance(other, Sequence) and not isinstance(other, str):
      if clone:
        other = [merge(None, _) for _ in other]

      if extend and isinstance(result, Sequence) and not isinstance(result, str):
        for value in other:
          if value not in result:
            result.append(value)
      else:
        result = other
    else:
      result = other

  return result

def pop(settings:Any, key:str, default = None, flatten:bool = True):
  if settings is None:
    return default

  try:
    if isinstance(settings, list):
      deleted = 0
      values = []

      for i in range(len(settings)):
        i -= deleted

        value = pop(settings[i], key, flatten=flatten)

        if not settings[i]:
          del settings[i]
          deleted += 1

        if value is None:
          continue

        if flatten and isinstance(value, list):
          values.extend(value)
        else:
          values.append(value)

      return values if values else default

    try:
      i = key.index('/')
      k = key[0:i]
      value = pop(settings[k], key[i + 1:], default, flatten)
      if not settings[k]: del settings[k]
      return value
    except ValueError:
      return settings.pop(key, default)
  except KeyError:
    return default

def update(settings:Any, other:Mapping) -> Mapping:
  if isinstance(settings, Sequence) and not isinstance(settings, str):
    try:
      for key, value in other.items():
        i = key.index('/')
        k = int(key[0:i])

        try:
          settings[k] = update(settings[k], {key[i + 1:]: value})
        except:
          settings[key] = value
    except:
      for item in settings:
        update(item, other)

    return settings

  if settings is None:
    settings = {}

  for key, value in other.items():
    try:
      i = key.index('/')
      k = key[0:i]
      settings[k] = update(settings.get(k), {key[i + 1:]: value})
    except:
      settings[key] = value

  return settings

def pprint(data, **opts):
  opts.setdefault('explicit_start', False)
  opts.setdefault('sort_keys', False)
  opts.setdefault('stream', stdout)
  dump_yaml(merge({}, data), **opts)

class Descriptor():
  def __init__(self, key, default=None):
    self.key = key
    self.default = default

  def __get__(self, obj, objtype=None):
    return obj.get(self.key, self.default)

  def __set__(self, obj, value):
    obj.update({self.key: self.default if value is None else value})

class Settings(UserDict):
  def __init__(self, data:Mapping=None, clone:bool=False, **opts):
    super().__init__()

    if clone:
      self.merge(data, clone=clone, **opts)
    elif data is not None:
      self.data = data

  def __str__(self):
    output = StringIO()
    self.print(stream=output)
    return output.getvalue()

  def copy(self):
    return Settings(self.data, extend=False, clone=True)

  def extend(self, *others, **opts):
    return self.merge(*others, extend=True, **opts)

  def filterkeys(self, pattern) -> Mapping:
    pattern = re.compile(pattern)
    return {k: v for k, v in self.items() if pattern.match(k)}

  def filter(self, patterns, true=True, literally=False):
    return {k: v for k, v in self.items() if match(v, patterns, true, literally)}

  def get(self, key, default=None, flatten=True):
    return get(self.data, key, default, flatten)

  def format(self, key, args, default=None):
    return getformat(self, key, args, default)

  def match(self, patterns, true=True, literally=False, default=None):
    return match(self, patterns, true=true, literally=literally, default=default)

  def merge(self, *others, **opts):
    merge(self.data, *others, **opts)
    return self

  def pop(self, key, default=None, flatten=True):
    return pop(self.data, key, default, flatten)

  def update(self, *others, **kwds):
    for other in others:
      update(self.data, other)

    update(self.data, kwds)

    return self

  def mapping(self, *keys):
    mapping = {}

    for k in keys:
      value = self.get(k)

      if value is not None:
        mapping[k] = value

    return mapping

  def print(self, **opts):
    pprint(self, **opts)

  @classmethod
  def dump(self, filename:str, data, **opts):
    data = merge({}, data)

    with open(filename, 'w') as fp:
      if filename.endswith('.json'):
        opts.setdefault('indent', 2)
        dump_json(data, fp, **opts)
        print(file=fp)
      else:
        dump_yaml(data, stream=fp, **opts)

  @classmethod
  def load(cls, filename:str, **opts):
    opts.setdefault('Loader', FullLoader)

    with open(filename) as fp:
      data = load_yaml(fp, **opts)

    return Settings(data)

class UserObject:
  pass
