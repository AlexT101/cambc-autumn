# cambc-autumn

Our entry for Cambridge Battlecode 2026a (cambc2026a).

## Language

We are writing our bot entirely in **C++**. Ignore the Rust, Python and OCaml material: the `sdk/rust`, `sdk/python` and `sdk/ocaml` folders and the non-C++ pages in `docs/`. The relevant docs are:

- [docs/handbook/](docs/handbook/) and [docs/champions/](docs/champions/): game rules (language-independent)
- [docs/guides/cpp/](docs/guides/cpp/): C++ guides
- [docs/api/cpp.md](docs/api/cpp.md): C++ API reference
- [sdk/cpp/cambc.h](sdk/cpp/cambc.h): the SDK header itself

## Docs

[docs/](docs/README.md) is a local mirror of the online handbook, champion pages, guides and Bot API reference (all four languages), with images. Regenerate it with `cd tools/docs-sync && npm install && node sync.mjs`.
