import time

n = int(input())
# Partial solution: fast on batches 1-2, slow on batches 3-4
if n >= 3:
    time.sleep(0.8)
else:
    time.sleep(0.01)
print(n)
