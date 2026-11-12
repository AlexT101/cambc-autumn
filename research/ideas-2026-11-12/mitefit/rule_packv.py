"""rule_pack.py with the pack led by Vesper (LONE default 0.5, until r200).   py rule_packv.py BODY_DIR [LONE]"""
import sys, subprocess
subprocess.run([sys.executable, __file__.replace('rule_packv.py', 'rule_pack.py'), sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else '0.5', '200', 'vesper'], check=True)
