h, w = map(int, input().split())

n = 1
for y in range(h):
    print(*(n + x for x in range(w)))
    n += w
