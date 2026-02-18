import random
import string

*nums, typ, chars = input().split()
seed, maxT, maxL, maxB = map(int, nums)
random.seed(seed)
minL = max(1, int(maxL * 0.9))

cifry = ""
if "0" in chars:
    cifry += string.digits
if "a" in chars:
    cifry += string.ascii_lowercase
if "A" in chars:
    cifry += string.ascii_uppercase

print(maxT)
for _ in range(maxT):
    if typ == "random":
        base = random.randint(2, maxB)
        cif = random.sample(cifry, base)
        l = random.randint(minL, maxL)
        res = [random.choice(cif) for _ in range(l)]
    elif typ == "same":
        c = random.choice(cifry)
        res = [c] * random.randint(1, maxL)
    else:
        assert False
    print("".join(res))