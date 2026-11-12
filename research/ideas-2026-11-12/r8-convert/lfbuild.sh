#!/bin/bash
# lfbuild.sh NAME...: private release builds of bots/variants/rc-NAME for livefork_rc.py (c-NAME; "ref" builds rc-524).
source ~/tmp-offload/r8-convert/env.sh
LF=$HOME/tmp-offload/r8-convert/lf/bots; mkdir -p $LF
for n in "$@"; do
  src=bots/variants/rc-$n; [ "$n" = ref ] && src=bots/variants/rc-524
  rm -rf $LF/c-$n; mkdir -p $LF/c-$n; cp -r $src/src $LF/c-$n/src
  cambc build --release $LF/c-$n 2>&1 | grep -E "error|built"
done
