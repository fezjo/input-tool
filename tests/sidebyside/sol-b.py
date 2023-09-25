h, w = map(int, input().split())

n = 1
for y in range(h - h // 7):
    print(*(x + (x % 11 == 0) for x in range(n, n + w)))
    n += w