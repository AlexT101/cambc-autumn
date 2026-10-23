#!/usr/bin/env sh
set -eu

repo=$(CDPATH= cd -- "$(dirname -- "$0")/../.." && pwd)
bin=$(mktemp "${TMPDIR:-/tmp}/willow-support-mailbox.XXXXXX")
trap 'rm -f "$bin"' EXIT HUP INT TERM
${CXX:-c++} -std=c++20 -Wall -Wextra -Werror "$repo/tools/fixtures/willow_support_mailbox.cpp" -o "$bin"
"$bin"
printf '%s\n' 'Willow support mailbox source fixtures passed.'
