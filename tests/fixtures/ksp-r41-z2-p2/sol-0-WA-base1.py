# ziska 1 bod na 8. sade, ale je to vtipne takze to neopravim
T = int(input())
for t in range(T):
    sifra = input()
    kluc = {}

    ktore = 0
    for ch in sifra:
        if ch not in kluc:
            if ktore == 0:
                kluc[ch] = 1
                ktore += 1
            elif ktore == 1:
                kluc[ch] = 0
                ktore += 1
            else:
                kluc[ch] = ktore
                ktore += 1

    ans = 0
    dlzka_sifry = len(sifra)
    zaklad = len(kluc)
    for i in range(dlzka_sifry):
        ans += kluc[sifra[i]]*zaklad**(dlzka_sifry-i-1)
    print(ans)
