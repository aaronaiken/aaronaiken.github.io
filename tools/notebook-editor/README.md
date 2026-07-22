# notebook-editor bundle

The cockpit notebook's CodeMirror 6 iA-Writer editor, ported from
`~/projects/48pages-app/frontend/src/lib/codemirror/notebook.ts` + `Editor.svelte`
so the two apps share the same editor. The cockpit is no-build at runtime, so
this is bundled ONCE into `static/notebook-editor.js` and vendored.

## Rebuild
```
cd tools/notebook-editor
npm install
npx esbuild entry.js --bundle --format=iife --minify --target=es2019 \
  --outfile=../../static/notebook-editor.js
```
`entry.js` exposes `window.NotebookEditor.create(hostEl, { doc, placeholder, onUpdate, onKeydown })`.
The editor styles itself via `--np-*` CSS vars (mapped to cockpit tokens in the
notebook page). Keep in sync with 48pages' notebook.ts when its editor changes.
