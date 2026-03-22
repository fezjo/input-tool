import sys

for value in map(int, sys.stdin):
    if value == 100:
        break
    print(value, flush=True)
