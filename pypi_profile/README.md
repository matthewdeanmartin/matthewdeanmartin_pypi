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
