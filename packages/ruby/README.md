# docpipe

Ruby wrapper for Docpipe. Requires the Python package `docpipe-core` to be installed and available to `python3`.
Set `DOCPIPE_PYTHON=/path/to/python` when the Python engine is installed in a virtualenv.

```ruby
require "docpipe"

doc = Docpipe.parse("invoice.pdf")
puts doc.markdown
```
