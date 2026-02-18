def solve():
    s = input()
    nastavene = dict()
    left = [9, 8, 7, 6, 5, 4, 3, 2, 0, 1]
    for c in s:
        if c not in nastavene:
            nastavene[c] = left.pop()
    mini = "".join(map(str, (nastavene[c] for c in s)))
    base = max(2, len(nastavene))
    res = int(mini, base)
    print(res)

TC = int(input())
for _ in range(TC):
    solve()