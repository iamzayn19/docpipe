# docpipe

Node.js wrapper for Docpipe. Requires the Python package `docpipe-core` to be installed and available to `python3`.

```js
import { parse } from "docpipe";

const doc = await parse("invoice.pdf");
console.log(doc.markdown);
```
