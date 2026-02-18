import time

n = int(input())
# Outlier: fast on batches 1-3, very slow on batch 4
if n == 4:
    time.sleep(0.6)
else:
    time.sleep(0.01)
print(n)
