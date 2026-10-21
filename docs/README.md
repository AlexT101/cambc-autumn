# CAMBC 2026a documentation (local mirror)

Mirror of the online handbook at https://2026a.battlecode.co.uk/game/docs and the Bot API reference at https://2026a.battlecode.co.uk/game/api, synced 2026-10-21. Regenerate with `cd tools/docs-sync && npm install && node sync.mjs`.

## Game rules

1. [The game](./handbook/01-objective.md)
2. [Drafting](./handbook/02-draft.md)
3. [A champion turn](./handbook/03-your-first-turn.md)
4. [Maps & movement](./handbook/04-maps-and-movement.md)
5. [Camps & capture](./handbook/05-camps.md)
6. [Gems & altars](./handbook/06-gems-and-scoring.md)
7. [Combat & abilities](./handbook/07-combat.md)
8. [Items & gold](./handbook/08-items.md)
9. [Vision & wards](./handbook/09-vision.md)
10. [Death, recall & recovery](./handbook/10-death-and-recall.md)
11. [Fuel](./handbook/11-fuel.md)
12. [Shared memory](./handbook/12-shared-memory.md)

- [Glossary](./handbook/glossary.md)
- [Patch notes](./patch-notes.md)

## Champions

- [Champion roster](./champions/README.md) (roster and stat comparison)
- [Cassi & Issac](./champions/cassi-and-issac.md)
- [Ryth](./champions/ryth.md)
- [Vesper Vale](./champions/vesper-vale.md)
- [Prism](./champions/prism.md)
- [Stellar](./champions/stellar.md)
- [Vendetta](./champions/vendetta.md)
- [Marcella](./champions/marcella.md)
- [Tavi](./champions/tavi.md)
- [Willow](./champions/willow.md)
- [Ren](./champions/ren.md)
- [Varg](./champions/varg.md)
- [Heart of Ruin](./champions/heart-of-ruin.md)

## Guides

| Guide | C++ | Rust | Python | OCaml |
| --- | --- | --- | --- | --- |
| Getting Started | [C++](./guides/cpp/first-bot.md) | [Rust](./guides/rust/first-bot.md) | [Python](./guides/python/first-bot.md) | [OCaml](./guides/ocaml/first-bot.md) |
| Bitboards | [C++](./guides/cpp/bitboards.md) | [Rust](./guides/rust/bitboards.md) | [Python](./guides/python/bitboards.md) | [OCaml](./guides/ocaml/bitboards.md) |
| Distance Fields | [C++](./guides/cpp/distance-fields.md) | [Rust](./guides/rust/distance-fields.md) | [Python](./guides/python/distance-fields.md) | [OCaml](./guides/ocaml/distance-fields.md) |
| VSCode | [C++](./guides/cpp/vscode.md) | [Rust](./guides/rust/vscode.md) | [Python](./guides/python/vscode.md) | [OCaml](./guides/ocaml/vscode.md) |

## Bot API reference

- [C++](./api/cpp.md)
- [Rust](./api/rust.md)
- [Python](./api/python.md)
- [OCaml](./api/ocaml.md)

## LLM exports

The single-file Markdown exports the site offers for coding assistants: [llm/](./llm/README.md).

## Notes on this mirror

- Interactive diagrams are shown as the site's text description. Their full on-screen text (step-by-step walkthroughs, labels) is in a collapsible block under each one. Some of it adds rule detail not in the plain prose.
- Inline decorative icons are omitted. Images such as the sample map, terrain tiles and champion art are in [images/](./images/).
- API entries keep the signature, description, parameters and any hand-written examples. The site's auto-generated one-line examples are left out.
