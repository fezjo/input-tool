# Generátor

Generátor je program, ktorý berie na vstupe jeden riadok (kde dáte čo chcete, napríklad dve čísla, maximálne $n$ a $m$.) Tento program vypíše, normálne na `stdout`, jeden vstup úlohy.

Dávajte si pozor, aby bol vypísaný vstup korektný, žiadne medzery na koncoch riadkov, dodržujte limity, čo sľubujete v zadaní (toto všetko vieme automatizovane zaručiť s pomocou validátora).

Jedna z vecí, čo je dobré robiť, je generovať viacero typov vstupov &ndash; povedzme náhodné čísla, veľa clustrov rovnakých, samé párne lebo vtedy je bruteforce pomalý, atď. To je dobré riešiť tak, že jedno z čísel, čo generátor dostane na vstupe je typ, podľa ktorého sa rozhodne, čo vygeneruje.

Generátor sa bežne volá `gen` (príponu si `input-tool` vie domyslieť, takže `gen.py`, `gen.cpp`, `gen.pas`, ... je všetko obsiahnté pod `gen`). Ak sa váš generátor volá inak, treba to povedať testeru pomocou prepínača `-g`.

Keď chcete commitnúť vstupy na git, commitujete zdrojový kód generátoru a `idf`, nie binárku a vygenerované vstupy.

O zvyšné veci by sa mal postarať `itool generate`.

### Spúšťanie

Pokiaľ robíte vstupy do KSP, odporúčané je púšťať `itool generate idf` bez prepínačov, aby ostatní vedúci vedeli vygenerovať rovnaké vstupy. Prepínače slúžia hlavne na to, ak robíte vstupy pre nejakú inú súťaž, kde sú iné prípony/ iná priečinková štruktúra. Iné prepínače zasa pomáhajú pri debugovaní.

Pokiaľ potrebujete robiť zveriny, napríklad použiť viac generátorov na jednu úlohu, toto sa dá špecifikovať v IDF.

```bash
# Odporúčané je použiť defaultný tvar:
$ itool generate idf

# Keď potrebujete, dá sa však spraviť mnoho iných vecí
$ itool generate --input . --inext input -g gen-special.cpp -q < idf

# Pre pochopenie predošlého riadku spustite
$ itool generate -h
```

**Pozor** si treba dávať na to, že `itool generate`, ak mu nepovieme prepínačom inak, zmaže všetky staré vstupy, okrem samplov.

# Používaj IDF ako mág

V tomto texte si prezradíme nejak pokročilé funkcie a fičúrie IDF. Niektoré z nich sa vám môžu hodiť.

## Základné použitie IDF

IDF (Input Description File) je súbor, ktorý popisuje, ako vyzerajú sady a vstupy. Jeden riadok IDF slúži na vyrobenie jedného vstupu (až na špeciálne prípady popísané nižšie). Každý takýto riadok poslúži ako vstup pre generátor a to, čo generátor vypľuje sa uloží do správneho súboru, napr. `02.a.in`. Čiže do IDF chcete obvykle písať veci ako maximálne $n$ (alebo aj presné $n$), typ vstupu, počet hrán grafu, atď., ale to už je na generátore, aby sa rozhodol, čo s tými číslami spraví.

Asi je fajn upozorniť, že zo začiatku a konca každého riadku v IDF sú odstránené biele znaky. Hlavný účel IDF totiž je, aby určoval, čo dostane na vstupe genrátor, nie ako presne vyzerá výsledný vstup. Keďže je možné použiť aj príkazy typu `cat` ako generátor, biele znaky vedia niekedy zavážiť.

Vstupy v jednej sade sú postupne písmenkované `a`..`z` (ak je ich veľa, tak sa použije viac písmen).

Sady v IDF oddeľujeme práznymi riadkami. Sady sú číslované `1`..`9`, ak je ich napr. 20, tak `01`..`20`.

### Príklad IDF

```perl
10 1000 ciara
20 1000 nahodne
30 1000 hviezda

1000 1000000 ciara
1000 1000000 nahodne
```

Vyrobí postupne vstupy `1.a.in`, `1.b.in`, `1.c.in`, `2.a.in`, `2.b.in`. V tomto návode (aj v tom, čo vypisuje `itool generate`) sa používa nasledovná notácia

```
1.a.in  <  10 1000 ciara
```

čo znamená, že generátoru dáme na vstup `"10 1000 ciara"` a to, čo generátor vypľuje, sa uloží do súboru `1.a.in`.

## Špeciálne premenné

- `{batch}` &ndash; označenie sady (môže byť napríklad aj '001')
- `{name}` &ndash; označenie vstupu v sade
- `{id}` &ndash; poradie vstupu od začiatku IDF
- `{rand}` &ndash; pseudonáhodné číslo z [0, 2\*\*31)
- **`{nazov_premennej}` &ndash; hodnota premennej (vieme si vytvárať vlastné premenné v YAML formáte**
- `{{nazov_premennej}}` &ndash; priamy text '`{nazov_premennej}`'

Ak chcete svojmu generátoru povedať, aký vstup vyrába, nie je problém. Nasledujúci IDF:

```perl
{batch} {name} {id}
{batch} {name} {id} 47

{batch} {name} {id}
{id} {name}
{{name}} {{id}}
```

Vyrobí vstupy podľa:

```
1.a.in  <  1 a 1
1.b.in  <  1 b 2 47
        .
2.a.in  <  2 a 3
2.b.in  <  4 b
2.c.in  <  {name} {id}
```

**Ak chcete niečim inicializovať `seed` vo svojom generátore, tak rozumný nápad je `{id}`**, pretože to je deterministické a zároveň unikátne pre každý vstup. Deterministické vstupy majú výhodu, že ak niekto iný pustí `itool generate` s rovnakými parametrami a rovnakým IDF, dostane rovnaké vstupy.

## Efekty znakov '`#`', '`$`', '`~`', `\`'

- Riadky začínajúce '`#`' sú ignorované (čiže sú to komentáre).
- Riadky začínajúce znakom '`~`' majú tento znak odstránený so začiatku a ďalej sú immúnne voči špeciálnym efektom, s výjnimkou '`\`' na konci riadku.
- Riadok začínajúci '`$`' nie je chápaný ako popis vstupu, ale ako konfigurácia pre nasledujúce vstupy. Môžeme napríklad nastaviť `$ name: xyz, batch: abc` a všetky nasledujúce vstupy sa budú volať `abc.xyz.in`.
- Riadky **končiace** '`\`' majú nasledujúci riadok ako súčasť toho istého vstupu

### Konfigurácia pomocou '`$`'

Konfigurácia platí až po najbližší riadok začínajúci `$`. Ak sa riadok začína `$+`, tak sa pridáva do konfigurácie, ak sa začína iba `$`, tak sa konfigurácia resetuje.

Ak sa viacero vstupov volá rovnako, jednoducho sa premažú, preto treba používať tieto konfigurátory s rozumom.

Konfigurovať vieme:

- názov sady (`batch`)
- názov vstupu v sade (`name`)
- prefix pre názov vstupu (`class`)
- generátor (`gen`)
- ľubovoľé vlastné premenné v YAML formáte, príklady:
  - formát `$ key1: value1, key2: value2, ...` &ndash; teda oddeľovač parametrov je `,`, za `:` musí byť medzera
  - `$ premenna: 5`
  - `$ p1: abc, p2: 5, p3: 0b101, p4: 1e9, p5: !eval 2 ** 10 - 1`
  - `$ zverina: !eval "import random; " ".join(map(str, [random.randint(0, 2**16-1) for x in range(10)]))"`

Keďže whitespace-y slúžia na oddeľovanie parametrov, nepoužívajte ich v hodnotách parametrov.

Táto fičúra sa môže hodiť na riešenie nasledovných problémov:

- Mám Bujov generátor a Janov generátor, každý má svoj IDF. Chcem aby neboli kolízie medzi názvami vstupov.  
   _Riešenie:_
  Na začiatku Bujovho IDF dáme `$ class: b` a na začiatku Janovho `$ class: j`. Pustím `itool generate -g gen-buj idf-buj && itool generate -g gen-jano idf-jano -k` a vygeneruje mi to vstupy s disjunktnými názvami (napr. `1.ba.in` a `1.ja.in`). Všimnite si `-k` v druhom spustení, ktoré spôsobí, aby sa nezmazali Bujove vstupy.
- Mám tri generátory, a chcem mať len jeden IDF.  
  _Riešenie:_ Použijem `$ gen: nazovgeneratora`, na správnych miestach.
- Chcem vygenerovať aj sample.  
  _Riešenie:_ Na koniec IDF pridám `$ batch: 00.sample` a za to parametre sample vstupov. Pozor, sample dávame na koniec, aby sa nám nepokazilo číslovanie ostatných sád.

### Príklady správania konfigurátorov

- ### IDF príklad 1

  ```perl
  10
  20
  $ class: prvocislo-
  37
  47
  $ name: odpoved
  # všimnime si, že s predošlým riadkom prestalo platiť class: prvocislo-
  42

  $ batch: 0.sample
  1
  2

  $ name: este-som-zabudol-jeden
  8
  ```

  Vyrobí vstupy takto:

  ```
                  0.sample.a.in  <  1
                  0.sample.b.in  <  2
                                .
                        1.a.in  <  10
                        1.b.in  <  20
                  1.odpoved.in  <  42
              1.prvocislo-c.in  <  37
              1.prvocislo-d.in  <  47
                                .
    3.este-som-zabudol-jeden.in  <  8
  ```

  Všimnite si, že posledný vstup má číslo sady 3 a nie 2. Totiž druhá sada je tá sample, ktorá sa len inak volá. Preto je dôležité dávať sample a custom sady na koniec.

- ### IDF príklad 2

  ```perl
  # komentár
  platí to len # na začiatku riadku
  a neplatí to pri \
  # viacriadkových vstupoch
  ~# ak chcem začat mriežkou, použijem ~
  platia efekty {{name}} {name}
  ~neplatia efekty {{name}} {name}
  $ name: z
  konfigurátor sa vzťahuje aj na premenné: {name}
  ```

  Sa interpretuje takto:

  ```
  platí to len # na začiatku riadku
  a neplatí to pri \n# viacriadkových vstupoch
  # ak chcem začat mriežkou, použijem ~
  platia efekty {name} d
  neplatia efekty {{name}} {name}
  konfigurátor sa vzťahuje aj na premenné: z
  ```

### IDF príklad 3

Máme vstupy prebraté z inej súťaže, ale chceme si spraviť aj nejaké vlastné:

```perl
# najprv vygenerujeme prvú sadu z prebratých vstupov
$ gen: sh
cat sutazne-vstupy/01.a.in
cat sutazne-vstupy/01.b.in
# teraz si zresetujeme generátor na defaultný a vygenerujeme si vlastné vstupy
$
{id} 1000

# a rovnako aj druhú sadu
$ gen: sh
cat sutazne-vstupy/02.a.in
$
{id} 1000000
{id} 1000000
```

## Viacriadkové vstupy

Ak chcete, dať svojmu generátoru viac riadkový vstup, použite '`\`'. Ak riadok končí znakom '`\`', nasledujúci riadok bude tiež súčasťou tohto vstupu. Prípadné efekty znakov '`#`', '`$`', '`~`', na začiatku ďalšieho riadku sa nevykonávajú.

Príklad:

```perl
$ gen: cat, batch: 0.sample
4\
1 2 3 4
3\
    1 2 3
```

Vyrobí dva sample vstupy. Všimnite si, že v IDF sa ignorujú biele znaky na začiatkoch a koncoch riadkov.

```
4
1 2 3 4
```

```
3
1 2 3
```

## Generatívny popis vstupov

Ak chceme určiť nielen typ vstupu, ale podrobnejšie, čo má generátor vyrobiť, môžeme použiť generatívny popis vstupov. V ňom generátoru dáme postupnosť príkazov, ktoré má vykonať. Toto sa hodí, ak chceme generovať napríklad rôznorodé stromy so špecifickou štruktúrou. Uvedieme príklad, ako to môže vyzerať na generovanie postupnosti čísel.

```perl
# array <count> <x_1> <x_2> ... <x_count> -- vygeneruje postupnosť čísel
# random <count> <lo> <hi> -- vygeneruje <count> náhodných čísel z intervalu [lo, hi]
# range <lo> <hi> -- vygeneruje postupnosť čísel z intervalu [lo, hi]
# shuffle -- premieša postupnosť čísel

$ n: !eval 1e6
# vygenerujeme postupnosť náhodných čísel od 1 do 50 
{id} {n} random {n} 1 50
# vygenerujeme náhodnú permutáciu čísel od 1 do n
{id} {n} range 1 {n} shuffle
# špecíalna permutácia
{id} {n} array 5 2 4 6 8 10 range 11 {n} array 5 1 3 5 7 9
```

Naprogramovať generátor, ktorý bude vedieť interpretovať takýto popis nie je o nič ťažšie, ako naprogramovať generátor ktorý vykonáva jednotlivé príkazy. Výhoda je, že takto môžeme z jednoduchých príkazov vygenerovať zložité štruktúry, pre ktoré by sme inak museli písať jednotlivé podobné typy generátorov.

Kód generátora, ktorý by vedel interpretovať takýto popis:

```cpp
#include <bits/stdc++.h>
using namespace std;

mt19937_64 mt;
long rnd(long lo, long hi) { return lo + mt() % (hi - lo + 1); }
long getl() { long double x; if (!(cin >> x)) assert(!"input error"); return x; }

int main() {
    long id = getl(), n = getl();
    mt.seed(id);

    vector<long> v;
    string cmd;
    while (cin >> cmd) {
        if (cmd == "array") {
            long cnt = getl();
            for (long i = 0; i < cnt; i++) v.push_back(getl());
        } else if (cmd == "random") {
            long cnt = getl(), lo = getl(), hi = getl();
            for (long i = 0; i < cnt; i++) v.push_back(rnd(lo, hi));
        } else if (cmd == "range") {
            long lo = getl(), hi = getl();
            for (long i = lo; i <= hi; i++) v.push_back(i);
        } else if (cmd == "shuffle") {
            shuffle(v.begin(), v.end(), mt);
        } else {
            cerr << "unknown command: " << cmd << "\n";
            assert(!"unknown command");
        }
    }
    assert(v.size() == n);

    cout << n << '\n';
    for (long i = 0; i < n; i++) cout << v[i] << " \n"[i == n - 1];
}
```