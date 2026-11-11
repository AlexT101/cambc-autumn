import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

# --analysis DIR must be in the environment before analysis.data is imported (worker processes import it afresh).
for i, a in enumerate(sys.argv):
    if a == '--analysis' and i + 1 < len(sys.argv):
        os.environ['CAMBC_ANALYSIS'] = sys.argv[i + 1]
    elif a.startswith('--analysis='):
        os.environ['CAMBC_ANALYSIS'] = a.split('=', 1)[1]

from analysis.cli import main

if __name__ == '__main__':
    sys.exit(main())
