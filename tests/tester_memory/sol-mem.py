import sys

n = int(sys.stdin.readline().strip())
try:
    data = [0] * (n * 1_000_000)
    print(len(data))
except MemoryError:
    raise SystemExit(1)
