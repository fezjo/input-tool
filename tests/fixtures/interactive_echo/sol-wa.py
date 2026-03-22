import sys

for value in map(int, sys.stdin):
    print(value + (value == 100), flush=True)
