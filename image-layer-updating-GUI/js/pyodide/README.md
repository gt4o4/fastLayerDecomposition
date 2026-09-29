# Vendored Pyodide

[Pyodide](https://pyodide.org/) 314.0.7 and the packages `layer-worker.js` loads, so the GUI doesn't depend on a CDN.
The files were downloaded from `https://cdn.jsdelivr.net/pyodide/v314.0.7/full/`:

* `pyodide.mjs`, `pyodide.asm.mjs`, `pyodide.asm.wasm`, `python_stdlib.zip`, `pyodide-lock.json`: the Pyodide runtime (MPL-2.0)
* `numpy-*.whl` (BSD-3-Clause) and `scipy-*.whl` (BSD-3-Clause): the only packages we load. They have no other Pyodide package dependencies.

To update Pyodide, download those files for the new version (the wheel file names are in `pyodide-lock.json`) and replace these.
If `layer-worker.js` loads more packages, also download them and their dependencies (listed under `depends` in `pyodide-lock.json`).
