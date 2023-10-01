from .exceptions import Error, PatternError
from .settings import get, getformat, merge, update, pop
from .template import jinja
from collections import UserDict
from collections.abc import Mapping
from json import dumps as json_encode, loads as json_decode
from pathlib import PurePosixPath
from slugify import slugify as fnslugify
from zlib import adler32, crc32
import hashlib
import re

slugify_regex = r'[^-a-zA-Z0-9_]+'

def conflits(properties:Mapping, args:Mapping, prefix:str='', root=None) -> list:
  keys = []

  if args is None:
    args = {}

  if root is None:
    root = args

  for key, prop in properties.items():
    condition = prop.get('when')

    try:
      if condition and not jinja.compile_expression(condition)(_=root, **args):
        continue
    except Exception as e:
      raise Error(key + '/when', *e.args)

    alias = prop.get('alias', key)
    value = args.get(alias)

    if value is None:
      continue

    conflits_with = prop.get('conflits_with')

    if conflits_with:
      if isinstance(conflits_with, str):
        conflits_with = [conflits_with]

      for _ in conflits_with:
        keys.append(prefix + _)

      continue

    props = prop.get('properties')

    if props:
      key = prop.get('use', key)
      keys.extend(conflits(props, value, prefix + key + '/', root))

  return keys

def compute(prop:Mapping, value, args:Mapping):
  type_ = prop.get('type')

  if type_ in ['json', 'string'] and not isinstance(value, str):
    value = json_encode(value)

  translator = prop.get('translate')

  if translator:
    key = value if isinstance(value, (str, bool, int, float, complex)) else str(value)
    value = translator.get(key, value)

  expr = prop.get('expr')

  if expr:
    try:
      value = jinja.compile_expression(expr)(this=value, **args)
    except Exception as e:
      raise Error('expr', *e.args)

  if not isinstance(value, str):
    return value

  patterns = prop.get('pattern')

  if patterns:
    if not isinstance(patterns, list):
      patterns = [patterns]

    for _ in patterns:
      _ = re.compile(_).match(value)

      if _:
        merge(args, _.groupdict({}))
        break

  algorithm = prop.get('hash')

  if algorithm:
    value = value.encode()
    fn = {"adler32": adler32, "crc32": crc32}.get(algorithm)
    value = '{:x}'.format(fn(value) & 0xffffffff) if fn else hashlib.new(algorithm, value).hexdigest()

  format_spec = prop.get('format')

  if format_spec:
    try:
      value = format_spec.format(value, **args)
    except KeyError as e:
      raise KeyError('format', *e.args)

  return value

def getvalue(prop:Mapping, args:Mapping, key:str):
  value = args.get(key)

  if value is None:
    value = getformat(prop, 'value', args)

  return value

def inherit(properties:Mapping):
  inherited = {}

  for key, prop in properties.items():
    if not prop.get('inherit', False):
      continue

    props = prop.get('properties')

    if props:
      props = inherit(props)

      if not props:
        continue

    prop = prop.copy()
    prop['ignore'] = True
    prop['sync'] = False

    if props:
      prop['properties'] = props

    prop.pop('alias', None)
    prop.pop('use', None)

    inherited[prop.get('alias', key)] = prop

  return inherited

def init(properties:Mapping, args:Mapping, defaults:bool=True, slugs:bool=True, root:Mapping=None) -> Mapping:
  if args is None:
    args = {}

  if root is None:
    root = args

  args_ = {'_': root, **args}

  for key, prop in properties.items():
    condition = prop.get('when')

    try:
      if condition and not jinja.compile_expression(condition)(**args_):
        continue
    except Exception as e:
      raise Error(key + '/when', *e.args)

    alias = prop.get('alias', key)

    try:
      value = getvalue(prop, args_, alias)
    except:
      value = None

    props = prop.get('properties')

    if props:
      try:
        value = merge(value, init(props, value, defaults, slugs, root), clone=False)
      except KeyError as e:
        raise KeyError(key, 'properties', *e.args)
      except Error as e:
        raise Error(key + '/properties/' + e.args[0], *e.args[1:])

      if not value:
        continue
    else:
      primary_key = prop.get('primary_key', False)

      if defaults and value is None and (primary_key or prop.get('ignore', False)):
        try:
          value = getformat(prop, 'default', args_)
        except:
          pass

      try:
        value = compute(prop, value, args_)
      except KeyError as e:
        raise KeyError(key, *e.args)
      except Error as e:
        raise Error(key + '/' + e.args[0], *e.args[1:])

      if value is None:
        continue

      if slugs and primary_key:
        alias_ = alias + '_'
        value_ = fnslugify(str(value), lowercase=False, regex_pattern=slugify_regex)
        args[alias_] = value_
        args_[alias_] = value_

    if isinstance(value, Mapping):
      unset = prop.get('unset', [])
      i = -1

      for item in unset:
        i += 1

        if isinstance(item, str):
          pop(value, item)
          continue

        condition = item.get('when')

        try:
          _ = (not condition or jinja.compile_expression(condition)(**args))
        except Exception as e:
          raise Error(key + '/unset/' + i + '/when', *e.args)

        if _:
          pop(value, item.get('key'))

    args[alias] = value
    args_[alias] = value

  return args

def onbeforesaving(properties:Mapping, settings:Mapping, root:Mapping=None) -> Mapping:
  if settings is None:
    return settings

  if root is None:
    root = settings

  for key, prop in properties.items():
    if prop.get('ignore', False):
      continue

    key = prop.get('use', key)
    value = get(settings, key)
    props = prop.get('properties')

    if props:
      try:
        onbeforesaving(props, value, root)
      except Error as e:
        raise Error(key + '/properties/' + e.args[0], *e.args[1:])

      if not value:
        pop(settings, key)
    else:
      expr = prop.get('onbeforesaving')

      if expr:
        try:
          jinja.compile_expression(expr)(_=root, __=settings, this=value, **settings)
        except Exception as e:
          raise Error(key + '/onbeforesaving', *e.args)

      if value is None:
        if not prop.get('nullable', False):
          pop(settings, key)

  return settings

def sync(properties:Mapping, settings:Mapping):
  if settings is None:
    settings = {}

  this = {}

  for key, prop in properties.items():
    sync_key = prop.get('sync', key)

    if sync_key is False:
      continue

    if isinstance(sync_key, list):
      for k in sync_key:
        value = get(settings, k)

        if value is not None:
          break
    else:
      value = get(settings, sync_key)

    if value is None:
      continue

    alias = prop.get('alias', key)
    props = prop.get('properties')

    if props:
      value = sync(props, value)

      if not value:
        continue

    this[alias] = value

  return this

def tosettings(properties:Mapping, args:Mapping, defaults:bool=True, root:Mapping=None):
  if args is None:
    args = {}

  this = {}

  if root is None:
    root = args

  args_ = {'_': root, **args}

  for key, prop in properties.items():
    if prop.get('ignore', False):
      continue

    condition = prop.get('when')

    try:
      if condition and not jinja.compile_expression(condition)(**args_):
        continue
    except Exception as e:
      raise Error(key + '/when', *e.args)

    alias = prop.get('alias', key)
    value = args.get(alias)
    props = prop.get('properties')

    try:
      if props:
        try:
          value = tosettings(props, value, defaults, root)
        except Error as e:
          raise Error(key + '/properties/' + e.args[0], *e.args[1:])

        if not value:
          continue

        settings = value
      else:
        if value is None and defaults:
          try:
            value = getformat(prop, 'default', args_)
          except Exception as e:
            pass

          value = compute(prop, value, args_)

        type_ = prop.get('type', 'string')

        if type_ == 'list' or type_.startswith('list('):
          if value is not None:
            if isinstance(value, str):
              try:
                value = json_decode(value)
              except:
                pass

            if not isinstance(value, list):
              value = [value]

            if not value:
              value = None

          settings = value
        else:
          computed = prop.get('computed')

          if computed:
            try:
              settings = '${' + computed.format(value, **args_) + '}'
            except KeyError as e:
              raise KeyError('computed', *e.args)
          else:
            settings = value

        if settings is None:
          if defaults and prop.get('required', False):
            raise ValueError(alias)

          continue

      if value is not None:
        args[alias] = value
        args_[alias] = value

      key = prop.get('use', key)
      merge(this, update({}, {key: settings}), clone=False)
    except KeyError as e:
      raise KeyError(key, *e.args)

  return this

def walk(properties:Mapping, callback, prefix:str='') -> dict:
  for key, prop in properties.items():
    alias = prop.get('alias', key)
    props = prop.get('properties')

    if props:
      walk(props, callback, prefix + alias + '/')
    else:
      callback(prefix + alias, prop)

  return properties

class Properties(UserDict):
  def __init__(self, owner, cfg:Mapping, key:str):
    super().__init__(get(cfg, key))
    self.owner = owner
    self.key = key
    self.context = PurePosixPath(owner.name, self.key)

    def inherit(alias, prop):
      if alias in owner.path:
        prop.setdefault('inherit', True)

    self.walk(inherit)

  def __call__(self, args:Mapping, defaults:bool=True, slugs:bool=True) -> dict:
    args = merge({}, args)

    try:
      return init(self, args, defaults=defaults, slugs=slugs)
    except KeyError as e:
      raise PatternError(self.owner.name, self.key, *e.args)
    except Error as e:
      raise Error(str(self.context / e.args[0]), *e.args[1:])

  def _inherit(self):
    resource = self.owner
    parent = resource.parent

    if parent:
      parent = parent.properties
      # Inherit missing path properties
      inherited = inherit(parent)

      if inherited:
        if resource.address == 'variable':
          for prop in inherited.values():
            prop.pop('computed', None)
            prop.pop('ignore', False)
            prop.setdefault('type', 'string')

        self.data = merge(inherited, self.data)

    pattern = re.compile('\[([^[\]]+)\]')
    keys = re.findall('(?<!{){([^{}]+)}', resource.source)
    keys = [pattern.sub(r'/\1', _) for _ in keys]

    def setdefault(alias, prop):
      unset = []

      for key, value in prop.items():
        if value is None:
          unset.append(key)
      
      for key in unset:
        del prop[key]

      if alias in keys:
        prop.setdefault('inherit', True)
        prop.setdefault('primary_key', True)

    self.walk(setdefault)
    self.parent = parent

  def conflits(self, args:Mapping) -> list:
    return conflits(self.data, args)

  def heritage(self, args:Mapping) -> dict:
    this = {}

    def callback(alias, prop):
      if prop.get('inherit', False) or prop.get('primary_key', False):
        value = get(args, alias)

        if value is not None:
          update(this, {alias: value})

    self.walk(callback)

    return this

  def onbeforesaving(self, settings):
    return onbeforesaving(self.data, settings)

  def primarykey(self, args:Mapping, slugs:Mapping=None, required:set=None) -> dict:
    this = {}

    def callback(alias, prop):
      if prop.get('primary_key', False):
        value = get(args, alias)

        if value is None:
          if required is not None and prop.get('required', True):
            required.add(alias)
        else:
          update(this, {alias: value})

          if slugs is not None:
            alias += '_'
            value = get(args, alias)

            if value is not None:
              update(slugs, {alias: value})

    self.walk(callback)

    return this

  def remote(self, args:Mapping) -> dict:
    this = {}

    def callback(alias, prop):
      if prop.get('sync', True) != False:
        value = get(args, alias)

        if value is not None:
          update(this, {alias: value})        

    self.walk(callback)

    return this

  def sync(self, settings:Mapping) -> dict:
    return sync(self, settings)

  def tosettings(self, args:Mapping, defaults:bool=True) -> dict:
    try:
      settings = tosettings(self, args, defaults=defaults)
    except KeyError as e:
      raise PatternError(self.owner.name, self.key, *e.args)

    if self.owner.address == 'variable':
      for key, prop in self.items():
        if prop.get('ignore', False):
          continue

        key = prop.get('use', key)

        try:
          key.index('/')
          continue
        except ValueError:
          pass

        value = settings.get(key)

        if value is None and not prop.get('nullable', False):
          continue

        value = {'default': value}

        for k, _ in prop.items():
          if k in ['description', 'type', 'validation', 'sensitive']:
            value[k] = _

        settings[key] = value

    return settings.get('.', settings)

  def walk(self, callback):
    return walk(self, callback)
