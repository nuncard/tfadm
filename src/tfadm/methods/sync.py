from . import Method
from ..exceptions import Error, PatternError, RequiredArgument
from ..settings import match, merge, pprint, Descriptor
from ..template import jinja
from collections.abc import Mapping
from json import dumps as tojson
from shlex import split as splitcmd, join as joincmd
from subprocess import check_output
from yaml import load as loadyaml, FullLoader
from click import secho

class Sync(Method):
  when = Descriptor('when', {})

  class Chache:
    def __init__(self, cmd:str, settings:Mapping):
      self.cmd = cmd
      self.settings = settings

  def __init__(self, owner, cfg:Mapping, key:str):
    super().__init__(owner, cfg, key + '/sync')
    self.cache = None

    for action in ['describe', 'list']:
      format_specs = self.data.get(action)

      if format_specs:
        if not isinstance(format_specs, list):
          format_specs = [format_specs]

        i = 0

        for format_spec in format_specs:
          if isinstance(format_spec, str):
            format_specs[i] = splitcmd(format_spec)
          i += 1

        self[action] = format_specs

  def _inherit(self):
    super()._inherit()

    parent = None
    resource = self.owner
    _ = resource.parent
    parent_name = self.get('parent')
    key = str(self.key)
    depends_on = None

    while _:
      parent = _.get(key)

      if parent and (parent_name is None or _.name == parent_name):
        break

      depends_on = _.name
      _ = _.parent

    if not parent and parent_name is not None:
      raise Error(str(self.context / 'parent'), 'No parent with the given name', parent_name)

    self.parent = parent

    if parent_name is not None and depends_on not in resource.depends_on:
      resource.depends_on.append(depends_on)

  def __call__(self, filters=None, **opts):
    terraform_import = opts.get('import', False)
    recursive = opts.get('recursive', False)
    resource = self.owner

    def update(args):
      args = resource('update', args, defaults=False, overwrite=True)

      if terraform_import:
        root = resource.format('root', args)
        state = resource.state.get(root)

        resource('terraform', 'chdir', root)

        if state is None:
          resource('terraform', 'init')
          resource('terraform', 'show')

        resource('terraform', 'import', args)
        resource.trigger('import', args)

      if recursive:
        args = resource.properties.heritage(args)
        resource.owner.each(lambda r, args: r('sync', args, **opts), resource, args)

    return self.describe(filters, update, force=opts.get('force', False))

  def describe(self, filters:Mapping, callback, **opts) -> int:
    return self.execute('describe', filters, callback, fallback='list', **opts)

  def list(self, filters:Mapping, callback, **opts) -> int:
    return self.execute('list', filters, callback, fallback='describe', **opts)

  def execute(self, action:str, filters:Mapping, callback, fallback:str=None, **opts) -> int:
    parent = self.parent
    format_specs = self.get(action)

    if not format_specs and fallback:
      format_specs = self.get(fallback)
      action = fallback
      fallback = None

    if not format_specs:
      return parent.list(filters, callback) if parent else 0

    i = 0
    count = len(format_specs)
    props = self.owner.properties
    args = props(filters, defaults=False, slugs=False)
    pprops = parent.owner.properties if parent else None
    context = str(self.context) + '.' + action + '()'

    while i < count:
      try:
        cmd_args = self.format('{}/{}'.format(action, i), args)
        err = None
        break
      except PatternError as e:
        print(e)
        err = e
        i += 1

    if err:
      count = 0

      if fallback and self.get(fallback):
        count = self.execute(fallback, filters, lambda _: self.execute(action, merge({}, filters, props.heritage(_)), callback))
      elif parent:
        count = parent.list(filters, lambda _: self.execute(action, merge({}, filters, pprops.heritage(_)), callback))

      if count > 0:
        return count

      pprint({context + '.arguments': args})
      raise err

    cmd = joincmd(cmd_args)

    if self.cache and self.cache.cmd == cmd:
      settings = self.cache.settings
      print('$', cmd, '(cached)')
    else:
      secho('$ {}'.format(cmd), bold=True)
      settings = loadyaml(check_output(cmd_args), Loader=FullLoader)
      self.cache = self.Chache(cmd, settings)

    if not settings:
      print(context + ': No objects found.')
      return 0

    if not isinstance(settings, list):
      settings = [settings]

    filters = props(filters, defaults=False, slugs=False)
    filters_ = props.remote(filters)
    heritage = pprops.heritage(filters) if self.parent else {}

    count = 0
    condition = self.when

    for args in settings:
      args = props.sync(args)
      args = merge(merge({}, heritage), args, clone=False)
      args_ = props(args, defaults=False, slugs=False)

      if filters_:
        if not match(args_, filters_, literally=True):
          continue

      if condition and not opts.get('force', False):
        if isinstance(condition, str):
          try:
            if not jinja.compile_expression(condition)(**args):
              continue
          except Exception as e:
            raise Error(str(self.context / 'when'), *e.args)
        elif not match(args, condition):
          continue

      if parent:
        required = set()
        pprops.primarykey(args_, required=required)

        if required:
          required.clear()
          print(self.owner.name + ".primary_key:", props.primarykey(args_, required=required))
          print(self.owner.name + ": Missing argument:", ', '.join(required))
          _ = parent.list(pprops.heritage(args), lambda _: callback(merge(pprops.heritage(_), args, clone=False)))

          if _ > 0:
            count += _
            continue

          raise RequiredArgument(self.owner.name, required)

      callback(args)
      count += 1

    if count == 0:
      ctx = str(self.context)

      if filters_:
        print('{}.{}(): No matches for the given filter: {}'.format(ctx, action, tojson(filters_)))
      else:
        print('{}/when: No matches for the given expression: {}'.format(ctx, condition))

    return count
