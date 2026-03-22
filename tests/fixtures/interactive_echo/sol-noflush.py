import sys

for value in map(int, sys.stdin):
    print(value, flush=value < 100)
