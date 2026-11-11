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
references that land in your `.htb` files. Saving, adding, deleting or renaming a bot's `.htb` files or headers
regenerates it, including changes made outside VS Code (a git pull). Types of `auto` variables show on hover;
to show them inline, set `"[htb]": { "editor.inlayHints.enabled": "on" }`.

## Writing a bot

Put the `.htb` files straight in the bot folder, `bots/<bot>/*.htb` (subfolders are fine). `bots/archives/htb-starter` is
cambc 3.0.4's C++ starter (`cambc new --lang cpp`) written this way; it plays the same games as the C++ original. Your own headers (`.h`, `.hpp`) in the bot folder are copied into `src/` as they are.

    python3 tools/htb/hgen.py <bot>             # regenerate src/ (no name: every .htb bot)
    python3 tools/htb/hgen.py --watch           # regenerate on every save while you work
    python3 tools/htb/htbcheck.py <bot>         # check a bot from the command line: file:line:col errors
    cambc build <bot> / cambc run ... / cambc submit <bot>

Run hgen before `cambc build`, `run` and `submit` (the extension does it on save). Commit `src/` with the bot,
since it's what cambc builds.

- `src/headers/<name>.h`: what `<name>.htb` declares (classes with method declarations, enums, constants,
  globals, prototypes, templates); `src/<name>.inl`: its function bodies; `src/unity.cpp`: every header, then every
  body, as one translation unit, so calls inline across files.
- Functions marked `inline`, `constexpr` or `consteval` are kept whole in a header instead of in `src/<name>.inl`
  (methods: their body stays in the class), and can still call each other in any order. `constexpr` and
  `consteval` ones are in `src/headers/<name>.h`, in order, so constants can use them; `inline` functions and
  templates are in `src/headers/<name>.inline.h`, after every class, since their bodies may reach any class.
- Never edit `src/`: hgen rewrites it, and refuses to touch a `src/` holding files it didn't write.
- Anything can be used before it's defined, across files and folders, including a class's nested types above
  their definition (in the editor those still get underlined, because clangd reads the class as written).
- The whole bot compiles as one unit, so two files can't both have a `static` function or global with the same
  name, and a file-level `using namespace std;` reaches every file; hgen prints a note for both.
- Every file sees the library headers (`<...>`) any file includes, and globals start up after the globals their
  initializers read (also through the functions and constructors they call).
- `#if`/`#ifdef` around code works anywhere, at file level or in a class (`#ifdef CAMBC_DEBUG` for debug-only code):
  whatever hgen moves keeps its conditions. `#if 0` is left out; include guards are fine.
- A forgotten `;` after a class (Java has none) is added, with a note; the editor underlines it with a quick fix.
- Each file's macros keep their own values, even if another file defines the same macro.
- A `.cpp` file in the bot folder isn't built (cambc builds `src/`); hgen notes it.

## What's here

| File | |
|---|---|
| `hgen.py` | the generator; also writes `.cambc/hgen/` and the bot's `.clangd` so clangd understands each file |
| `htbcheck.py` | command-line checker: bracket/string errors per file, then cambc's compiler on the generated code |
| `install.py` | the setup above |
| `vscode/` | the VS Code extension (source and the packaged `htb-*.vsix`); see its README to change it |
| `tests/` | the test suite: `python3 tools/htb/tests/run.py` (cases in `tests/cases/`; see `run.py`'s header) |

## Tests

    python3 tools/htb/tests/run.py              # every case: about 45 s
    python3 tools/htb/tests/run.py 07_templates --keep

Each case in `tests/cases/` is a small bot that defines things in awkward ways (circular, across nested folders,
Java order, C-style, macros, CRLF files...). Every case is generated, built and run natively with its output
checked (or its errors checked against the right `.htb` lines), compiled with cambc's own compiler, opened in clangd
the way the extension does, and fuzzed: each file cut at every token, with every token deleted, with junk inserted
everywhere and with random multi-token edits must never crash or hang hgen. Two more checks: `lifecycle` (editing,
deleting and renaming files, stray files in `src/`, `--check`, `--watch`) and `stress` (a 20,000-line file, 300
files, nesting 100 deep). Run it after changing hgen.
