# Contributing

## Setup

```bash
git clone https://github.com/{{ cookiecutter.github_username }}/{{ cookiecutter.github_repo }}.git
cd {{ cookiecutter.github_repo }}
uv sync
```

## Running checks

```bash
make check
```

## Running tests only

```bash
make test
```

## Before submitting a PR

```bash
make prerelease
```
