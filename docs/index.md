# matthewdeanmartin

Identity package for Matthew Dean Martin — the profile page PyPI won't let you make.

## Installation

```bash
pip install matthewdeanmartin
```

## Usage

You can run the tool directly:

```bash
matthewdeanmartin
```

Or via python:

```bash
python -m matthewdeanmartin
```

### Output Formats

**Plain Text (Default)**

```bash
matthewdeanmartin
```

**JSON**

```bash
matthewdeanmartin --json
```

**Markdown**

```bash
matthewdeanmartin --markdown
```

## Why?

PyPI doesn't provide rich profile pages for maintainers. This package serves as a verifiable identity and trust signal. 

## Trust Signals

The package includes:
- Linked accounts (GitHub, LinkedIn, StackOverflow)
- PGP fingerprints
- Contact policies
- Continuity plans

## API Reference

```{eval-rst}
.. automodule:: matthewdeanmartin.__main__
   :members:
   :undoc-members:
   :show-inheritance:
```
