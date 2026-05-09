PyPI design system
==================

``pypi_ds`` is a standalone Jinja2 component package extracted from Warehouse's UI patterns.

What it includes
----------------

* layout shells under ``pypi_ds/templates/pypi_ds/layouts/``
* reusable component macros under ``pypi_ds/templates/pypi_ds/components/``
* example pages under ``pypi_ds/templates/pypi_ds/examples/``
* static assets under ``pypi_ds/static/``

Using it
--------

1. Add ``pypi_ds/templates`` to your Jinja loader search path.
2. Serve ``pypi_ds/static`` at a URL such as ``/static/pypi_ds``.
3. Render templates with ``asset_base='/static/pypi_ds'`` or the URL you choose.

Helper functions
----------------

Import these from ``pypi_ds.paths``:

* ``package_root_path()``
* ``template_root_path()``
* ``static_root_path()``

These return ``pathlib.Path`` objects you can use to wire the package into another app.
