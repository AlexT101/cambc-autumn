"""rule_packv.py at LONE 0.2: the pack follows Vesper more strongly.   py rule_packv2.py BODY_DIR"""
import sys, subprocess
subprocess.run([sys.executable, __file__.replace('rule_packv2.py', 'rule_packv.py'), sys.argv[1], '0.2'], check=True)
