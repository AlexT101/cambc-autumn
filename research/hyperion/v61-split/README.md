# v61 port, split

The v61 port (3d0f09a, af3ad8e; EXPERIMENTS "v61's features ported into astraeus") split into parts, each a patch on
astraeus deb288a's `src/` (apply with `patch -p0` from a copy of `bots/astraeus`), for separate A/Bs against deb288a. Each also carries v61's drafts (Vendetta in Vesper Vale's slot, Vesper
never drafted: params.h and draft.cc's pick_first_available, as at eb362e6):

- `retreat.patch`: Prism's safe step off a lethal tile and Heart of Ruin's escape-dash reserve (bot.cc retreat,
  abilities, self_abilities).
- `emblems.patch`: the v61 emblem rules as of 9d24efd (Hunter for Vendetta and Heart of Ruin, Prospector for Marcella
  with clusters on our walk and for Prism on cluster maps, on 3 picks Monster for everyone and Prospector on cluster
  maps; no Treasure fallback) and map_economy.h.
- `three.patch`: the 3-pick package (Tavi-map draft and leads, Tavi as gold farmer, pure-gold holder and Willow's
  mate, Tavi's Prospector then Hunter, Stellar to Marcella hand-off).
