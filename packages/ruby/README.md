# docpipe

Ruby wrapper for Docpipe. Requires the Python package `docpipe-core` to be installed and available to `python3`.

```ruby
require "docpipe"

doc = Docpipe.parse("invoice.pdf")
puts doc.markdown
```
