# tfadm - Terraform administrator

[Tfadm](https://github.com/nuncard/tfadm) (or Terraform Administrator) is a program that generates and modifies [terraform code](https://developer.hashicorp.com/terraform/language) in [JSON syntax](https://developer.hashicorp.com/terraform/language/syntax/json).

The goal is to help system administrators easily manage [Infrastructure as Code (IaC)](https://en.wikipedia.org/wiki/Infrastructure_as_code), simplify documentation, reduce training time for new employees, and enable users with little or no knowledge of terraform code to operate the system.

In no way does tfadm attempts to replace terraform command functionalities. Tfadm just enables you to automate the creation and modification of terraform code.

Some of tfadm features are:
- Generates and modifies terraform code in bulk;
- Converts existing infrastructure into terraform code;
- Associates existing infrastructure with the terraform resources, if not already under terraform management.
- Copies changes made directly to the infrastructure into terraform code;

## Install

Install and update using [pip](https://pip.pypa.io/en/stable/quickstart/):

```bash
python3 -m pip install -U tfadm
tfadm version
```

Install and update using pip and [virtual environments](https://docs.python.org/3/library/venv.html):

```bash
python3 -m venv --clear --upgrade-deps --prompt tfadm ~/.venv/tfadm
source ~/.venv/tfadm/bin/activate
pip install --upgrade pip
pip install -U tfadm
tfadm version
```

To leave your virtual environment, simply run:

```bash
deactivate
```

## Usage

`tfadm [OPTIONS] COMMAND [ARGS]...`

## Options

<dl>
  <dt><code>-V</code>, <code>--version</code></dt>
  <dd>Show the version and exit.</dd>
  <dt><code>-h</code>, <code>--help</code></dt>
  <dd>Show help message and exit.</dd>
</dl>

## Commands

<dl>
  <dt><code>create</code></dt>
  <dd>Creates an object from stdin.</dd>
  <dt><code>help</code></dt>
  <dd>Show help message and exit.</dd>
  <dt><code>resources</code></dt>
  <dd>Lists the available resources.</dd>
  <dt><code>sync</code></dt>
  <dd>Copies changes to the infrastructure into terraform code.</dd>
  <dt><code>update</code></dt>
  <dd>Updates an object from stdin.</dd>
  <dt><code>version</code></dt>
  <dd>Show the version and exit.</dd>
</dl>

Use `tfadm COMMAND --help` for more information about a given command.

## Resources

Tfadm depends on a set of configuration files (resources) to operate, in [YAML format](https://yaml.org/).

See [tfadm-resources](https://github.com/nuncard/tfadm-resources) to get started.

## Dependencies

- [$ click_](https://click.palletsprojects.com), to create the "beautiful" command line interface;
- [Jinja](https://jinja.palletsprojects.com), to allow code [expressions](https://jinja.palletsprojects.com/en/3.1.x/templates/#expressions) in resource files more safely (not yet used as a template engine);
- [parse](https://github.com/r1chardj0n3s/parse), to do the the opposite of [format()](https://docs.python.org/3/library/stdtypes.html#str.format) in a very specific situation, which most likely could be done with [regular expressions](https://docs.python.org/3/library/re.html);
- [python-slugify](https://github.com/un33k/python-slugify), python-slugify, to create slugs that can be used to name terraform blocks;
- [PyYAML](https://pyyaml.org/wiki/PyYAMLDocumentation), to parse configuration files and data from stdin and dump data to stdout.

## Author

tfadm was created by Nuno Cardoso.
