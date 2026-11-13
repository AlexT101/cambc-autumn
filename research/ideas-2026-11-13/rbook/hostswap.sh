#!/bin/bash
# Moves the book onto a new host bot: hostswap.sh SRC DST   (from the repo root)
#   SRC: a bot under bots/ (e.g. charybdis); DST: a new name under bots/variants.
# Makes variants/DST-base (SRC + fuel patches 01-02 where they are not in yet: the bench reference) and variants/DST
# (DST-base + the book code: rbook-x's diff from chy-525f, written to host.patch), benches DST-base, then prints the
# stage command. Stops on any patch reject.
set -e
SRC=$1; DST=$2; [ -n "$SRC" ] && [ -n "$DST" ] || { echo "usage: hostswap.sh SRC DST"; exit 2; }
R=research/ideas-2026-11-13/rbook; B=~/tmp-offload/rbook/bench; V=bots/variants
./copybot -f "$SRC" "variants/$DST-base"
for p in research/fuel-2026-11-13/patches/0*.diff; do
  if patch -d $V/$DST-base -p1 -R --dry-run -s -f < $p > /dev/null 2>&1; then echo "fuel patch in already: $p"
  else patch -d $V/$DST-base -p1 -s -f < $p; echo "fuel patch applied: $p"; fi
done
(cd $V && diff -ruN -x book_data.h -x .cambc chy-525f/src rbook-x/src) > $R/host.patch || true
./copybot -f "variants/$DST-base" "variants/$DST"
patch -d $V/$DST -p1 -s -f < $R/host.patch   # paths are chy-525f/src/... -> -p1 leaves src/...
cp $V/rbook-x/src/book/book_data.h $V/$DST/src/book/book_data.h
find $V/$DST $V/$DST-base -name '*.rej' -o -name '*.orig' | grep . && { echo "patch leftovers above"; exit 1; } || true
[ -n "$NOBENCH" ] || python3 tools/fuel/bench.py run variants/$DST-base --set wide --jobs 32 --out $B/$DST-base-100M.json > $B/$DST-base-100M.log 2>&1
[ -n "$NOBENCH" ] || python3 tools/fuel/bench.py run variants/$DST-base --maps $(cat ~/tmp-offload/rbook/fresh_bench.txt) --fuel 0 --jobs 32 \
        --out $B/$DST-base-fresh-0.json > $B/$DST-base-fresh-0.log 2>&1
echo "ready. Next (new WORK dir: symlink raw, ent; copy fp.json bad.json extra.tsv drop.txt keys.txt from x2):"
echo "  REF=$DST-base PRIO=seeded $R/stage.sh $DST WORK WORK/keys.txt --opp 'Intercontinental Fish:r8' --opp Mite:r9 --extra WORK/extra.tsv --force-versions 901,123"
echo "  (cd $R && python3 forcecheck.py --host variants/$DST --opp variants/$DST-base --work WORK)"
echo "Verify fails on entries whose picks the new draft no longer makes: drop them (pick_entries --drop) or force them."
