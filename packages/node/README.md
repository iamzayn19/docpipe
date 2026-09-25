# docpipe

Node.js wrapper for Docpipe. Requires the Python package `docpipe-core` to be installed and available to `python3`.
Set `DOCPIPE_PYTHON=/path/to/python` when the Python engine is installed in a virtualenv.

```js
import { parse } from "docpipe";

const doc = await parse("invoice.pdf");
console.log(doc.markdown);
```
