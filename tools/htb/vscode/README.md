# HTB extension for VS Code

The editor half of `.htb` (see [../README.md](../README.md)). Users install the packaged `htb-*.vsix` with
`python3 tools/htb/install.py`; this folder is only needed to change the extension.

- `extension.js`: registers the `htb` language, starts clangd for `.htb` files, reruns `tools/htb/hgen.py` when a bot's
  `.htb` files or headers are saved, added, deleted or renamed (in VS Code or outside it, e.g. by git), once per burst,
  and maps go to definition / references from the generated `src/` back to `.htb` lines (`map.js`, via hgen's `#line` markers).
- `syntaxes/htb.tmLanguage.json`: highlighting, borrowed from VS Code's C++ grammar.
- `lsp-test.js`: talks to clangd the way the extension does and prints diagnostics, completion, hover and the
  definition mapping for the example bot (`node lsp-test.js`, after `npm install`).

Rebuild after a change (bump `version` in package.json):

    npm install
    npx @vscode/vsce package --skip-license --allow-missing-repository
    python3 ../install.py
