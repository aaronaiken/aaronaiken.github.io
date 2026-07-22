// Cockpit notebook editor — a thin adapter around the 48pages CodeMirror 6
// "Instrument" editor. The editor CORE (decorations, dim-marks, live checkboxes,
// soft-block, 30px-grid theme) is imported DIRECTLY from 48pages so a rebuild
// tracks it — see build.mjs (`@48pages/notebook` aliases to the real file).
// Only the cockpit-facing create() API + EditorView wiring live here; the amber
// skin + serif font are applied via CSS in the cockpit (notebook.css).
//
// Update flow: when the 48pages editor improves, `npm run build` here + deploy.
import { EditorState } from '@codemirror/state';
import { EditorView, keymap, drawSelection, placeholder } from '@codemirror/view';
import { markdown } from '@codemirror/lang-markdown';
import { defaultKeymap, history, historyKeymap } from '@codemirror/commands';
import { notebookExtensions, LINE_UNIT_PX } from '@48pages/notebook';

const LINE_PX = LINE_UNIT_PX;

window.NotebookEditor = {
	LINE_PX,
	create: function (host, opts) {
		opts = opts || {};
		let full = false;
		const view = new EditorView({
			parent: host,
			state: EditorState.create({
				doc: opts.doc || '',
				extensions: [
					history(),
					keymap.of([...defaultKeymap, ...historyKeymap]),
					EditorView.lineWrapping,
					markdown(),
					drawSelection(),
					placeholder(opts.placeholder || ''),
					...notebookExtensions(() => full),
					EditorView.updateListener.of((u) => {
						if ((u.docChanged || u.selectionSet || u.geometryChanged) && opts.onUpdate) {
							const sel = u.state.selection.main;
							opts.onUpdate({
								text: u.state.doc.toString(),
								from: sel.from, to: sel.to,
								docChanged: u.docChanged,
								lineUnits: Math.max(1, Math.round(u.view.contentHeight / LINE_PX))
							});
						}
					}),
					EditorView.domEventHandlers({ keydown: (e) => { if (opts.onKeydown) opts.onKeydown(e); return false; } })
				]
			})
		});
		function currentBlock() {
			const text = view.state.doc.toString();
			const pos = view.state.selection.main.head;
			let start = text.lastIndexOf('\n\n', pos - 1); start = start === -1 ? 0 : start + 2;
			const endRel = text.indexOf('\n\n', pos); const end = endRel === -1 ? text.length : endRel;
			return { start, end, text: text.slice(start, end).replace(/^\s+|\s+$/g, '') };
		}
		return {
			view,
			getValue: () => view.state.doc.toString(),
			setValue: (text) => {
				if (text === view.state.doc.toString()) return;
				view.dispatch({ changes: { from: 0, to: view.state.doc.length, insert: text || '' } });
			},
			currentBlock,
			removeBlock: (blk) => {
				const text = view.state.doc.toString();
				const before = text.slice(0, blk.start).replace(/\n+$/, '');
				const after = text.slice(blk.end).replace(/^\n+/, '');
				const joined = before && after ? before + '\n\n' + after : before + after;
				view.dispatch({ changes: { from: 0, to: view.state.doc.length, insert: joined }, selection: { anchor: Math.min(before.length, joined.length) } });
			},
			appendText: (add) => {
				const text = view.state.doc.toString();
				const joined = (text.replace(/\n+$/, '') + (text.trim() ? '\n\n' : '') + add).replace(/^\n+/, '');
				view.dispatch({ changes: { from: 0, to: view.state.doc.length, insert: joined } });
			},
			setFull: (f) => { full = !!f; },
			lineUnits: () => Math.max(1, Math.round(view.contentHeight / LINE_PX)),
			focus: () => view.focus(),
			destroy: () => view.destroy()
		};
	}
};
