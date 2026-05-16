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
