// Bundle the cockpit notebook editor. Imports the 48pages editor CORE directly
// (`@48pages/notebook` → the real notebook.ts) so a rebuild tracks it. Forces every
// @codemirror/* + @lezer/* import (from here AND from 48pages) to resolve to THIS
// build's node_modules, so there's a single CodeMirror instance (mixing two breaks CM6).
//
//   npm install && npm run build      # -> ../../static/notebook-editor.js
//   P48PAGES_NOTEBOOK=/path/to/notebook.ts npm run build   # override the source path
import esbuild from 'esbuild';
import os from 'node:os';
import path from 'node:path';
import { createRequire } from 'node:module';
import { fileURLToPath } from 'node:url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const require = createRequire(path.join(__dirname, 'package.json'));

const P48 = process.env.P48PAGES_NOTEBOOK
	|| path.join(os.homedir(), 'projects/48pages-app/frontend/src/lib/codemirror/notebook.ts');

const forceLocalCM = {
	name: 'force-local-cm',
	setup(build) {
		build.onResolve({ filter: /^@(codemirror|lezer)\// }, (args) => {
			try { return { path: require.resolve(args.path) }; } catch (e) { return null; }
		});
	}
};

await esbuild.build({
	entryPoints: [path.join(__dirname, 'entry.js')],
	bundle: true,
	format: 'iife',
	minify: true,
	target: 'es2019',
	outfile: path.join(__dirname, '../../static/notebook-editor.js'),
	alias: { '@48pages/notebook': P48 },
	plugins: [forceLocalCM],
	logLevel: 'info'
});
console.log('built static/notebook-editor.js from', P48);
