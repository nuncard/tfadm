#!/usr/bin/env python

from sys import version_info, stdin

# TODO: Remove this check at some point in the future.
if version_info[0] < 3:
  raise ImportError('A recent version of Python 3 is required.')

from os.path import dirname, basename

__DIR__ = dirname(__file__)
__PACKAGE__ = basename(__DIR__)

if '__path__' not in globals():
  __path__ = [__DIR__]

from . import __version__
from .exceptions import Error, Required
from .resources import Resources, Resource
from .settings import merge
from collections.abc import Sequence
from subprocess import CalledProcessError
import click
import errno
import yaml

version_message = '{}, version {} from {} (Python {}.{})'.format(__PACKAGE__, __version__, __DIR__, *version_info[:2])

def main() -> int:
  try:
    cli()
    return 0
  except (Required, Error, yaml.scanner.ScannerError)  as e:
    code = 255
    click.secho('[Errno {}] {}'.format(code, str(e)), err=True, fg='red')
    return code
  except (FileNotFoundError, FileExistsError, PermissionError) as e:
    click.secho('[Errno {}] {}: {}'.format(*e.args, e.filename), err=True, fg='red')
    return e.errno
  except (KeyboardInterrupt, CalledProcessError):
    return errno.ECANCELED
  except SystemExit as code:
    return code

def read_args(resource:Resource, path:Sequence):
  paths = [path] if isinstance(path, str) else path

  if len(paths) == 1 and paths[0] == '-':
    return [_ for _ in yaml.safe_load_all(stdin)]

  args = []
  last = None
  path = None

  for path in paths:
    last = merge({}, last, clone=True)

    # Read arguments from standard input, if PATH is -
    if path == '-':
      # Overwrite PATH properties, if also set from standard input
      merge(last, yaml.safe_load(stdin), clone=False)
    else:
      # Properties linked to PATH are set automatically
      merge(last, resource.path(path), clone=False)
      args.append(last)

  if path == '-':
    args.append(last)

  return args

@click.group(context_settings={'help_option_names': ['-h', '--help']})
@click.version_option(__version__, '-V', '--version', prog_name=__PACKAGE__, message=version_message)
def cli():
  """Generates and modifies Terraform code in JSON format."""

@cli.command('help')
@click.pass_context
def cli_help(ctx):
  """Show this message and exit."""
  print(ctx.parent.get_help())

@cli.command('version')
def cli_version():
  """Show the version and exit."""
  print(version_message)

@cli.command('resources')
@click.argument('resource', required=False)
def cli_resources(resource=None):
  """Lists the available resources.

With RESOURCE, dump resource configuration to stdout.
"""
  resources = Resources()

  if resource is None:
    resources.loadAll()

    for name, resource in sorted(resources.items()):
      if not name.startswith('.'):
        print(name, resource.path)

        try:
          description = resource.description[0:resource.description.index("\n")]
        except:
          description = resource.description

        print(click.wrap_text(description, initial_indent='  ', subsequent_indent='  '), '\n')
  else:
    resource = _ = resources.load(resource)
    parents = []

    while _:
      parents.insert(0, _.name.replace('/', ':'))
      _ = _.parent

    print('---')
    print('#', '/'.join(parents))
    resource.print()

@cli.command('create')
@click.option(
  '--dry-run',
  default=False,
  help="Only print the object that would be saved, without saving it.",
  is_flag=True,
)
@click.option(
  '-o', '--overwrite',
  default=False,
  help="Overwrite the object, if exists.",
  is_flag=True,
)
@click.argument('resource')
@click.argument('path', required=False, nargs=-1)
def cli_create(resource, path=None, **opts):
  """Creates an object from stdin.

RESOURCE must be specified. Use 'tfadm resources' for a complete list of
available resources.

PATH is the virtual path of the the object. When PATH is -, reads object
properties from stdin.

If the object already exists, tfadm will error out, unless the '-o', or
'--overwrite' option is given.
"""
  resource = Resources().load(resource)

  for args in read_args(resource, path):
    resource('create', args, defaults=True, **opts)

@cli.command('update')
@click.option(
  '--dry-run',
  default=False,
  help="Only print the object that would be saved, without saving it.",
  is_flag=True,
)
@click.argument('resource')
@click.argument('path', required=False, nargs=-1)
@click.pass_context
def cli_update(ctx, resource, path=None, **opts):
  """Updates an object from stdin.

RESOURCE must be specified. Use 'tfadm resources' for a complete list of
available resources.

PATH is the filesystem path where the object is stored, relative to tfadm
project's root directory. When PATH is -, reads object attributes from stdin.

The object will be created if it doesn't exist.
"""
  resource = Resources().load(resource)

  for args in read_args(resource, path):
    resource('update', args, **opts)

@cli.command('sync')
@click.option(
  '-r', '--recursive',
  default=False,
  help='Copy resources and its sub-resources recursively.',
  is_flag=True,
)
@click.option(
  '--force',
  default=False,
  help='Ignores the `when` filter in the configuration, if any.',
  is_flag=True,
)
@click.option(
  '--import',
  default=False,
  help='Associate existing infrastructure with Terraform resources.',
  is_flag=True,
)
@click.argument('resource', required=False)
@click.argument('path', required=False, nargs=-1)
def cli_sync(resource, path=None, **opts):
  """Copies changes to the infrastructure into Terraform code.

Without RESOURCE, converts the existing infrastructure into Terraform code.

When RESOURCE or PATH is '-', filters existing infrastructure by stdin, copying
only matching objects. JSON and YAML formats are supported.

Use 'tfadm resources' for a complete list of available resources.
"""
  resources = Resources()

  if resource == '-' and not path:
    resource = None
    args = [_ for _ in yaml.safe_load_all(stdin)]
  elif resource is not None:
    resource = resources.load(resource)
    args = read_args(resource, path)

    if opts.get('recursive', False):
      resources.loadAll()
  else:
    args = None

  if not args:
    args = [None]

  for _ in args:
    if resource is None:
      resources.loadAll().each(lambda r, args: r('sync', args, **opts), None, _)
    else:
      resource('sync', _, **opts)

if __name__ == '__main__':
  exit(main())
