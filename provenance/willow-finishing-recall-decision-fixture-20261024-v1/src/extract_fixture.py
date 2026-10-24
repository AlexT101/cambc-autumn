#!/usr/bin/env python3
"""Extract exact production function bodies into the host fixture, rejecting source drift."""
from pathlib import Path
import argparse, hashlib, json

EXPECTED_BOT_CPP = '12b287870f0e516829ccd0ce47765391e273729af1529fdc3df2f719da060d46'
SIGNATURES = (
    'bool outmatched(const World& world, Pathing& pathing, bool* payout_relaxed_pack)',
    'bool want_home(const World& world, Pathing& pathing, Safety& safety, bool sieging, bool* payout_relaxed_pack = nullptr)',
    'bool continue_recall(const World& world, Pathing& pathing, Safety& safety, Memory& memory, std::optional<bool>& home)',
)

def extract_function(text: str, signature: str) -> str:
    start = text.index(signature)
    brace = text.index('{', start)
    depth = 0
    for i in range(brace, len(text)):
        if text[i] == '{': depth += 1
        elif text[i] == '}':
            depth -= 1
            if depth == 0:
                return text[start:i+1]
    raise ValueError(f'unclosed function: {signature}')

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--source',required=True,type=Path)
    ap.add_argument('--output',required=True,type=Path)
    args=ap.parse_args()
    raw=args.source.read_bytes()
    digest=hashlib.sha256(raw).hexdigest()
    if digest != EXPECTED_BOT_CPP:
        raise SystemExit(f'production source SHA mismatch: expected {EXPECTED_BOT_CPP}, got {digest}')
    source=raw.decode()
    bodies='\n\n'.join(extract_function(source,s) for s in SIGNATURES)
    prelude=Path(__file__).with_name('fixture_harness.cpp.in').read_text()
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(prelude.replace('/*PRODUCTION_FUNCTIONS*/',bodies))
    Path(__file__).with_name('extract-receipt.json').write_text(json.dumps({
        'schema':'production-source-extraction/v1','source_path':str(args.source),
        'source_sha256':digest,'functions':list(SIGNATURES),
        'generated_cpp_sha256':hashlib.sha256(args.output.read_bytes()).hexdigest(),
        'limits':'Exact bodies of outmatched, want_home, and continue_recall are compiled; surrounding world/native/helper methods are declared mocks.'
    },indent=2)+'\n')
if __name__=='__main__': main()
