#!/usr/bin/env sh
set -eu

repo=$(CDPATH= cd -- "$(dirname -- "$0")/../.." && pwd)
bin=$(mktemp "${TMPDIR:-/tmp}/willow-vesper-gold-value.XXXXXX")
trap 'rm -f "$bin"' EXIT HUP INT TERM
${CXX:-c++} -std=c++20 -Wall -Wextra -Werror "$repo/tools/fixtures/willow_vesper_gold_value.cpp" -o "$bin"
"$bin"
printf '%s\n' 'Willow/Vesper source fixtures passed.'
