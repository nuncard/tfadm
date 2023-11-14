from . import Method
from ..exceptions import RequiredArgument
from ..settings import match, merge, pop, pprint, Settings
from collections.abc import Mapping, ValuesView
from json import dumps as tojson
from os.path import dirname
from pathlib import Path
import errno

class Update(Method):
  def __init__(self, owner, cfg:Mapping, key:str):
    super().__init__(owner, cfg, key + '/update')

  def __call__(self, args:Mapping=None, defaults:bool=False, dry_run:bool=False, overwrite:bool=False):
    resource = self.owner
    context = str(self.context) + '()'
    props = resource.properties

    # Deep copy the arguments and prepare all auxiliary arguments
    args_ = props(args, defaults=defaults)

    # Use only primary key arguments to resolve the source file name
    pk_ = {}
    required = set()
    pk = props.primarykey(args_, pk_, required)

    if required:
      pprint({context + '.args': args_})
      raise RequiredArgument(context, ', '.join(required))

    merge(pk_, pk)

    try:
      # Load the current Terraform, if exists
      source = Path(resource.format('source', pk))
    except Exception as e:
      pprint({context + '.primary_key': pk})
      raise e

    try:
      terraform = resource.load(source)
      init = False
    except FileNotFoundError:
      terraform = Settings()
      init = True

    try:
      # Resolve the item's address within Terraform
      address = resource.format('address', args_)
    except Exception as e:
      pprint({context + '.arguments': args_})
      raise e

    # Control variable to know if it is creating or updating the resource
    settings = None

    if terraform:
      items = terraform.get(address)

      if items is None and address != resource.address:
        address_ = dirname(address)

        if address_ != '':
          items = terraform.get(address_)

          if isinstance(items, Mapping):
            items = items.values()

      if isinstance(items, (list, ValuesView)):
        # Using primary key to match items
        settings_ = props.tosettings(pk_, defaults=False)

        if settings_:
          for _ in items:
            # Exact match, no wildcards
            if match(_, settings_, literally=True, default=True):
              settings = _
              break
      else:
        settings = items

      # Discard old settings if `overwrite` option is enabled
      if isinstance(settings, Mapping) and overwrite:
        settings.clear()

    if settings:
      if defaults:
        raise FileExistsError(errno.EEXIST, '{}: Object already exists'.format(resource.name), tojson(pk))
      exists = True
    else:
      exists = False

    # Generate the template
    template = resource.template(args_)
    terraform.merge((template.copy() if dry_run else template), extend=True, clone=False)

    try:
      if exists:
        settings_ = props.tosettings(args_, defaults=False)
        merge(settings, settings_, extend=True, clone=False)
        action = 'Updated'
        created = False
      else:
        if not defaults:
          args_ = props(args)

        try:
          # Convert arguments to settings and validates the request as well
          settings_ = props.tosettings(args_)
        except ValueError as e:
          raise RequiredArgument(resource.name, *e.args)

        if settings is None:
          settings = settings_
          terraform.merge(Settings().update({address: settings}), extend=True, clone=False)
          action = 'Created'
        else:
          merge(settings, settings_, clone=False)
          action = 'Overwritten'

        created = True
    except Exception as e:
      pprint({context + '.arguments': args_})
      raise e

    conflicts_with = resource.conflicts_with

    if conflicts_with:
      if isinstance(conflicts_with, str):
        conflicts_with = [conflicts_with]

      for key in conflicts_with:
        terraform.pop(key)

    if dry_run:
      settings = settings_

    try:
      resource.beforesave(settings)
    except Exception as e:
      pprint({context + '.settings': settings})
      raise e

    if not dry_run:
      try:
          source_dir = source.parent
          source_dir.mkdir(parents=True, exist_ok=False)
          print(context + ': mkdir', str(source_dir))
      except FileExistsError:
        pass

    if terraform:
      if dry_run:
        template.merge(Settings().update({address: settings}), extend=True, clone=False).print(explicit_start=True, sort_keys=True)
        print('---')
      else:
        # Save the new Terraform to the file
        resource.dump(str(source), terraform, sort_keys=True)

      print(context + ':', action, source, address)

      heritage = props.heritage(args_)
      _ = merge({}, args, heritage)

      if init:
        resource.trigger('init', _, overwrite=overwrite, dry_run=dry_run)

      resource.trigger('change', _, overwrite=overwrite, dry_run=dry_run)

      if created:
        resource.trigger('create', _, overwrite=overwrite, dry_run=dry_run)
      else:
        resource.trigger('update', _, overwrite=overwrite, dry_run=dry_run)

    # --------------------------------------------------------------------------

    # Make sure the resource is a module
    if resource.module.file:
      try:
        filename = Path(resource.module.format('file', pk))
      except (Exception) as e:
        pprint({context + '.primary_key': pk})
        raise e

      try:
        address, settings_ = resource.module(args_)
      except (Exception) as e:
        pprint({context + '.arguments': args_})
        raise e

      # Load the current Terraform, if exists
      try:
        terraform = resource.module.load(str(filename))
      except FileNotFoundError:
        terraform = Settings()

      settings = terraform.get(address)

      if settings:
        if overwrite:
          settings.clear()
          action = 'Overwritten'
        else:
          action = 'Updated'
      else:
        action = 'Created'

      terraform_ = Settings().update({address: settings_})

      if dry_run:
        # Only print the object that would be saved, without saving it.
        terraform_.print(explicit_start=True, sort_keys=True)
        print('---')
      else:
        try:
          filename.parent.mkdir(parents=True, exist_ok=False)
          print(context + ': mkdir', str(filename.parent))
        except FileExistsError:
          pass

        resource.module.dump(str(filename), terraform.merge(terraform_, clone=False), sort_keys=True)

      print(context + ':', action, str(filename), address)

    return args_

class Create(Update):
  def __init__(self, owner, cfg:Mapping, key:str):
    super().__init__(owner, cfg, key)
    self.key = self.key.with_name('create')

  def __call__(self, args:Mapping=None, **opts):
    opts['defaults'] = True
    return super().__call__(args, **opts)
