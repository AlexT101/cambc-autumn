# .htb: C++ bots written like Java

An `.htb` file is C++ written the way you'd write Java: classes with their methods inside, no headers, no forward
declarations, files in any order, and every file can use what any other file defines. `hgen.py` turns a bot's `.htb`
files into the C++ that cambc builds; compile errors still point at your `.htb` lines.

## Setup (once)

    python3 tools/htb/install.py        (Windows: py tools\htb\install.py)

It generates and builds every `.htb` bot, installs the HTB extension into VS Code, and checks for clangd.
If clangd is missing: `brew install llvm` (macOS), `winget install LLVM.LLVM` (Windows), `sudo apt install clangd`
(Linux). Then **Developer: Reload Window** in VS Code.

In `.htb` files you then get squiggles while you type, completion and hover across files, and go to definition /
references that land in your `.htb` files. Saving a file regenerates its bot. Types of `auto` variables show on hover;
to show them inline, set `"[htb]": { "editor.inlayHints.enabled": "on" }`.

## Writing a bot

Put the `.htb` files straight in the bot folder, `bots/<bot>/*.htb` (subfolders are fine). `bots/htb-starter` is
the starter bot written this way. Your own headers (`.h`, `.hpp`) in the bot folder are copied into `src/` as they are.

    python3 tools/htb/hgen.py <bot>             # regenerate src/ (no name: every .htb bot)
    python3 tools/htb/hgen.py --watch           # regenerate on every save while you work
    python3 tools/htb/htbcheck.py <bot>         # check a bot from the command line: file:line:col errors
    cambc build <bot> / cambc run ... / cambc submit <bot>

Run hgen before `cambc build`, `run` and `submit` (the extension does it on save). Commit `src/` with the bot,
since it's what cambc builds.

- `src/headers/<name>.h`: what `<name>.htb` declares (classes with method declarations, enums, constants,
  globals, prototypes, templates); `src/<name>.inl`: its function bodies; `src/unity.cpp`: every header, then every
  body, as one translation unit, so calls inline across files.
- Never edit `src/`: hgen rewrites it, and refuses to touch a `src/` holding files it didn't write.
- The whole bot compiles as one unit, so two files can't both have a `static` function or global with the same name.
- `#if` at file level isn't supported; put it inside a function.

## What's here

| File | |
|---|---|
| `hgen.py` | the generator; also writes `.cambc/hgen/` and the bot's `.clangd` so clangd understands each file |
| `htbcheck.py` | command-line checker: bracket/string errors per file, then cambc's compiler on the generated code |
| `install.py` | the setup above |
| `vscode/` | the VS Code extension (source and the packaged `htb-*.vsix`); see its README to change it |
