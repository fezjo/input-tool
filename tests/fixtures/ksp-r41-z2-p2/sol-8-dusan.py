T = int(input())
for t in range(T):
    sifra = input()
    kluc = {}

    ktore = 0
    for znak in sifra:
        if znak not in kluc:
            if ktore == 0:
                kluc[znak] = 1
            elif ktore == 1:
                kluc[znak] = 0
            else:
                kluc[znak] = ktore
            ktore += 1

    odpoved = 0
    dlzka_sifry = len(sifra)
    zaklad = max(2, len(kluc))
    for i in range(dlzka_sifry):
        odpoved += kluc[sifra[i]]*zaklad**(dlzka_sifry-i-1)
    print(odpoved)
