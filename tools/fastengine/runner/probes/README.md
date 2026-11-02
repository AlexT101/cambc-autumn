# fastrunner probes

Bots that check fastrunner's WASI imports against stock cambc.
`wasi` prints every stdio/clock/random/path call's result on its first play turn; `wasi-fuel` prints the fuel each
call costs. Play each against any bot with `cambc run-batch` and with `fastrunner run-batch` (both modes) and
compare the bundles' members other than `.debug`: they matched on 2026-11-01.
