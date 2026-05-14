# pypi-profile

The missing PyPI profile page — `pipx`-installable, plugin-extensible.

## Install

```bash
pipx install pypi-profile
```

## Usage

```bash
pypi-profile --help
pypi-profile --version
```

## Plugins

Install any `pypi_profile.plugins` entry-point package alongside `pypi-profile` to contribute profile data.

Built-in example:

```bash
pipx inject pypi-profile matthewdeanmartin
```

## Legal

Apache license to match Warehouse license for theme.

Not associated with the PSF. TM logos removed from profile.

[Pypi is Trademark](https://pypi.org/trademarks/) of the Python Software Foundation.

[Pypi's Template and Theme](https://github.com/pypi/warehouse/blob/main/LICENSE) Apache from Warehouse.
