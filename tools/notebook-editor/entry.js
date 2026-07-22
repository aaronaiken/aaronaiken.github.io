// Cockpit notebook editor — a standalone bundle of the 48pages CodeMirror 6
// "Instrument" editor (ported verbatim from 48pages-app frontend/src/lib/codemirror/notebook.ts
// + Editor.svelte). Bundled once with esbuild into a single static file so the
// cockpit stays no-build. Exposes window.NotebookEditor.create(host, opts).
import { syntaxHighlighting, syntaxTree, HighlightStyle } from '@codemirror/language';
import { EditorState, RangeSetBuilder } from '@codemirror/state';
import { Decoration, EditorView, ViewPlugin, WidgetType, keymap, drawSelection, placeholder } from '@codemirror/view';
import { tags as t } from '@lezer/highlight';
import { markdown } from '@codemirror/lang-markdown';
import { defaultKeymap, history, historyKeymap } from '@codemirror/commands';

const LINE_PX = 30;

const highlightStyle = HighlightStyle.define([
	{ tag: t.heading, fontWeight: '600', color: 'var(--np-text-strong)' },
	{ tag: t.strong, fontWeight: '600', color: 'var(--np-text-strong)' },
	{ tag: t.emphasis, fontStyle: 'italic' },
	{ tag: t.strikethrough, textDecoration: 'line-through', color: 'var(--np-faint)' },
	{ tag: [t.link, t.url], color: 'var(--np-accent)', textDecoration: 'underline' },
	{ tag: t.monospace, fontFamily: "'IBM Plex Mono', ui-monospace, monospace", color: 'var(--np-muted)' },
	{ tag: t.quote, color: 'var(--np-muted)', fontStyle: 'italic' }
]);

const DIM_NODES = new Set([
	'HeaderMark', 'EmphasisMark', 'StrongMark', 'QuoteMark',
	'CodeMark', 'ListMark', 'LinkMark', 'StrikethroughMark'
]);
const dimMark = Decoration.mark({ class: 'cm-mark' });

function buildDimMarks(view) {
	const builder = new RangeSetBuilder();
	const cursorLine = view.state.doc.lineAt(view.state.selection.main.head).number;
	for (const { from, to } of view.visibleRanges) {
		syntaxTree(view.state).iterate({
			from, to,
			enter(node) {
				if (!DIM_NODES.has(node.name)) return;
				if (view.state.doc.lineAt(node.from).number !== cursorLine) {
					builder.add(node.from, node.to, dimMark);
				}
			}
		});
	}
	return builder.finish();
}

const dimMarksPlugin = ViewPlugin.fromClass(
	class {
		constructor(view) { this.decorations = buildDimMarks(view); }
		update(u) {
			if (u.docChanged || u.selectionSet || u.viewportChanged) this.decorations = buildDimMarks(u.view);
		}
	},
	{ decorations: (v) => v.decorations }
);

const TASK_RE = /^(\s*(?:[-*]\s+)?)(\[[ xX]\])/;

class CheckboxWidget extends WidgetType {
	constructor(checked, from) { super(); this.checked = checked; this.from = from; }
	eq(other) { return other.checked === this.checked && other.from === this.from; }
	toDOM(view) {
		const box = document.createElement('input');
		box.type = 'checkbox';
		box.checked = this.checked;
		box.className = 'cm-task-checkbox';
		box.setAttribute('aria-label', 'toggle task');
		box.addEventListener('mousedown', (e) => e.preventDefault());
		box.addEventListener('click', (e) => {
			e.preventDefault();
			view.dispatch({ changes: { from: this.from, to: this.from + 3, insert: this.checked ? '[ ]' : '[x]' } });
		});
		return box;
	}
	ignoreEvent() { return true; }
}

function buildCheckboxes(view) {
	const builder = new RangeSetBuilder();
	const { doc, selection } = view.state;
	const cursorLine = doc.lineAt(selection.main.head).number;
	for (const { from, to } of view.visibleRanges) {
		const first = doc.lineAt(from).number;
		const last = doc.lineAt(to).number;
		for (let n = first; n <= last; n++) {
			const line = doc.line(n);
			const m = TASK_RE.exec(line.text);
			if (m && n !== cursorLine) {
				const markerFrom = line.from + m[1].length;
				const checked = m[2][1].toLowerCase() === 'x';
				builder.add(markerFrom, markerFrom + 3, Decoration.replace({ widget: new CheckboxWidget(checked, markerFrom) }));
			}
		}
	}
	return builder.finish();
}

const taskCheckboxes = ViewPlugin.fromClass(
	class {
		constructor(view) { this.decorations = buildCheckboxes(view); }
		update(u) {
			if (u.docChanged || u.selectionSet || u.viewportChanged) this.decorations = buildCheckboxes(u.view);
		}
	},
	{
		decorations: (v) => v.decorations,
		provide: (plugin) => EditorView.atomicRanges.of((view) => view.plugin(plugin)?.decorations ?? Decoration.none)
	}
);

function softBlock(isFull) {
	return EditorState.transactionFilter.of((tr) => {
		if (!isFull() || !tr.docChanged) return tr;
		let delta = 0, insertedNonNewline = false;
		tr.changes.iterChanges((fromA, toA, fromB, toB, inserted) => {
			delta += toB - fromB - (toA - fromA);
			if (inserted.toString().replace(/\n/g, '').length > 0) insertedNonNewline = true;
		});
		return delta > 0 && insertedNonNewline ? [] : tr;
	});
}

const theme = EditorView.theme({
	'&': { height: '100%', color: 'var(--np-text)', backgroundColor: 'transparent' },
	'&.cm-focused': { outline: 'none' },
	'.cm-scroller': {
		fontFamily: "'Crimson Pro', Georgia, serif",
		fontSize: '17px',
		lineHeight: `${LINE_PX}px`,
		padding: '6px 0 28px',
		overflow: 'auto'
	},
	'.cm-content': {
		padding: '0 26px',
		caretColor: 'var(--np-accent)',
		minHeight: '100%',
		backgroundImage: 'repeating-linear-gradient(var(--np-bg), var(--np-bg) 29px, var(--np-grid) 30px)',
		backgroundPosition: '0 0'
	},
	'.cm-line': { padding: '0', lineHeight: `${LINE_PX}px` },
	'.cm-mark': { opacity: '0.32' },
	'.cm-task-checkbox': {
		appearance: 'none', width: '15px', height: '15px', margin: '0 2px 0 0',
		verticalAlign: '-2px', borderRadius: '3px', border: '1.5px solid var(--np-border-hi)',
		background: 'var(--np-bg)', cursor: 'pointer'
	},
	'.cm-task-checkbox:checked': { background: 'var(--np-accent)', borderColor: 'var(--np-accent)' },
	'.cm-task-checkbox:checked::after': {
		content: '""', display: 'block', width: '4px', height: '8px', margin: '0px auto',
		transform: 'translateY(1px) rotate(45deg)', borderRight: '2px solid var(--np-bg)', borderBottom: '2px solid var(--np-bg)'
	},
	'.cm-cursor, .cm-dropCursor': { borderLeftColor: 'var(--np-accent)' },
	'&.cm-focused .cm-selectionBackground, .cm-selectionBackground, ::selection': { backgroundColor: 'var(--np-accent-chip-bg)' },
	'.cm-placeholder': { color: 'var(--np-faint)', fontStyle: 'italic' }
});

function notebookExtensions(isFull) {
	return [theme, syntaxHighlighting(highlightStyle), dimMarksPlugin, taskCheckboxes, softBlock(isFull)];
}

// ---- cockpit-facing API ----
window.NotebookEditor = {
	LINE_PX: LINE_PX,
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
			let endRel = text.indexOf('\n\n', pos); const end = endRel === -1 ? text.length : endRel;
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
