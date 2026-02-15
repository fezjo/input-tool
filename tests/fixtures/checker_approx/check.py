import math
import sys

_inp, out_file, test_file = sys.argv[1:4]
with open(out_file) as f:
    expected = [line.strip() for line in f if line.strip()]
with open(test_file) as f:
    actual = [line.strip() for line in f if line.strip()]
if len(expected) != len(actual):
    raise SystemExit(1)
for e, a in zip(expected, actual):
    if not math.isclose(float(e), float(a), rel_tol=0.0, abs_tol=1e-6):
        raise SystemExit(1)
raise SystemExit(0)
