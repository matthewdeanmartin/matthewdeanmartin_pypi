# matthewdeanmartin

This is the missing pypi profile page for matthewdeanmartin.

It solves the problem of pypi not having a way to signal your identity across the web other than the trusted publisher
feature, which ties a build server to your ID. There is no known way to add a rel=me and you'd need to make updates to
all of your packages to update identity information displayed in the README.md.

This is the data package for pypi-profile, which uses signatures to substantiate claims that I control the
matthewdeanmartin account and various profile pages across the web.

[You can see the static one from here](https://matthewdeanmartin.github.io/matthewdeanmartin_pypi/).

`pypi-profile` plugin — contributes Matthew Martin's PyPI profile data.

## Install

```bash
pipx install pypi-profile
pipx inject pypi-profile matthewdeanmartin
```

## Want one of your own?

- Get the package [pypi-profile](https://pypi.org/project/pypi-profile/)
- Read the [docs](https://matthewdeanmartin-pypi.readthedocs.io/en/latest/)

## Project Links

- [GitHub](https://github.com/matthewdeanmartin/matthewdeanmartin_pypi)
- [PyPI](https://pypi.org/project/matthewdeanmartin/)
- [Bug Tracker](https://github.com/matthewdeanmartin/matthewdeanmartin_pypi/issues)
- [Change Log](https://github.com/matthewdeanmartin/matthewdeanmartin_pypi/blob/main/matthewdeanmartin/CHANGELOG.md)

## Python 3.15 verification — 2026-10-04

Three plugin tests and installed-wheel entry-point/data loading pass on 3.15.0rc3 with Pydantic prerelease wheels and on 3.14.7. Stable RC3 is blocked through the pypi-profile dependency. No runtime change or new native fallback was needed.

Dependencies were required to have published wheels; own pure-Python workspace wheels were built locally without build isolation. Locks were refreshed with uv lock --upgrade. Full developer stacks remain separately wheel-blocked (PyYAML or source-only linkcheckmd). No upstream reports or GitHub jobs were sent; bug filing belongs to the human operator.
