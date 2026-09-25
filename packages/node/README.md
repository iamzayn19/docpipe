# docpipe

Node.js wrapper for Docpipe. Requires the Python package `docpipe-core` to be installed and available to `python3`.
Set `DOCPIPE_PYTHON=/path/to/python` when the Python engine is installed in a virtualenv.

```bash
npm install @iamzayn19/docpipe
```

```js
import { parse } from "@iamzayn19/docpipe";

const doc = await parse("invoice.pdf");
console.log(doc.markdown);
```
