import sys

for value in map(int, sys.stdin):
    if value == 100:
        raise RuntimeError("crash at 100")
    print(value, flush=True)
