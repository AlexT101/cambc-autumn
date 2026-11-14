# river_cpp

River (origin/river/regression-hunt @ 8cfdc9ff) as plain C++: hgen's output from `bots/river/*.htb`, with the
`#line` directives and "generated, do not edit" banners removed, so it can be edited directly without the htb
toolchain. Same layout as before: `src/unity.cpp` includes `src/headers/*.h`, then every `src/*.inl` body, as one
translation unit.

Plays identical games to `bots/river` (match statistics identical vs astraeus on 00ambush, 00anvil, 00breadcrumbs,
100k fuel, release). Edits to `bots/river/*.htb` after 8cfdc9ff don't carry over here.
