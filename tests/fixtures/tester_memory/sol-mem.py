import resource
import sys

sys.setrecursionlimit(10**6)

for name in ["RLIMIT_AS", "RLIMIT_DATA", "RLIMIT_RSS", "RLIMIT_STACK", "RLIMIT_VMEM"]:
    if hasattr(resource, name):
        limit = getattr(resource, name)
        soft, hard = resource.getrlimit(limit)
        print(f"{name}: Soft: {soft} bytes, Hard: {hard} bytes", file=sys.stderr)


def f(level):
    a = chr(ord("a") + level) * 800  # allocate 1 KB per frame
    if level == 0:
        return 0
    return f(level - 1) + hash(a)


stack_mb, heap_mb = map(int, input().split())
data = [0] * (heap_mb * 1024**2 // 8)
print("Data: {:.3f}MB".format(sys.getsizeof(data) / 1024**2), file=sys.stderr)

# // 2 is too much, // 4 is too little (on 2nd batch without heap allocation)
f(stack_mb * 1024 // 3)
