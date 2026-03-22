import sys

for value in map(int, sys.stdin):
    if value == 100:
        raise RuntimeError("Crash on 100")
    print(value, flush=True)
