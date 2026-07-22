# notebook-editor bundle

The cockpit notebook's CodeMirror 6 iA-Writer editor. The editor CORE is the
48pages editor, imported DIRECTLY from `~/projects/48pages-app/frontend/src/lib/
codemirror/notebook.ts` at build time — so a rebuild tracks 48pages. The cockpit
is no-build at runtime, so this bundles ONCE into `static/notebook-editor.js`.

`entry.js` is only the cockpit adapter: the `window.NotebookEditor.create(host,
{ doc, placeholder, onUpdate, onKeydown })` API + the EditorView wiring. The amber
skin (`--np-*` vars) + the serif font are applied via CSS in the cockpit.

## Update the cockpit editor after improving 48pages
```
cd tools/notebook-editor
npm install          # first time only
npm run build        # -> ../../static/notebook-editor.js, from the 48pages source
# then commit static/notebook-editor.js + deploy
```
Override the source path with `P48PAGES_NOTEBOOK=/path/to/notebook.ts npm run build`.
build.mjs forces a single CodeMirror instance (mixing two copies breaks CM6).

## The eventual "automatic" path
True zero-step propagation happens when 48pages PUBLISHES the editor as a
consumable package/module the cockpit imports at runtime — a task for the 48pages
side. Until then, "one command + deploy" is the sync.
