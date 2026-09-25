# Release Guide

## Python

```bash
cd packages/python
python -m pip install -U build twine
python -m build
twine check dist/*
twine upload dist/*
```

Requires a PyPI token:

```bash
export TWINE_USERNAME=__token__
export TWINE_PASSWORD=pypi-...
```

## Node.js

```bash
cd packages/node
npm install
npm test
npm publish --access public
```

Requires:

```bash
npm login
```

## Ruby

```bash
cd packages/ruby
bundle install
bundle exec rake test
gem build docpipe.gemspec
gem push docpipe-*.gem
```

Requires:

```bash
gem signin
```

## Git Tag

```bash
git tag v0.1.0
git push origin main --tags
```
