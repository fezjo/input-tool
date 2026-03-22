import sys
import time

for value in map(int, sys.stdin):
    time.sleep(value / 10000)
    print(value, flush=True)
