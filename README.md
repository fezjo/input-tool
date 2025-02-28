## Zmeny voči jablkoj

<details>
<summary>Mergnuté zmeny</summary>

- **Podpora priečinkov v zozname programov** (automatické načítanie všetkých riešení, validátorov a checkera z priečinku)
- Časovanie
  - Desatinný timelimit `-t 0.5`
  - **Jazykový timelimit** `-t "3,cpp=1,py=5"`
  - Detailnejšie vypisovanie trvania programov
    - **Milisekundová presnosť**
    - Zobrazovanie celkového času namiesto _User time_
    - Vypisovanie _Real/User/System time_
    - TLE čas sa neráta do `Max time`
  - Varovný timelimit pomocou `--wtime`
- Lepšie predvolené nastavenia
  - **Preskakovanie zvyšných vstupov** v sade po odmietnutí (vypnúť cez `-F`)
  - Štatistiky po vyhodnotení (vypnúť cez `--no-statistics`)
  - **Kompilovanie C++ s optimalizáciami a novším štandardom**
  - Zvýšené limity pre pamäť a zásobník
  - Deduplikovanie programov na vstupe (vypnúť cez `--dupprog`)
  - **Paralelné generovanie vstupov a testovanie** (pomocou prepínača `-j`)
- Podpora alternatívnych Python interpreterov (**PyPy**) pomocou `--pythoncmd cmd`
- **Rozšírená funkcionalita IDF o vlastné premenné**
- Možnosť nemať nainštalovaný `time`
- Zrušená podpora pre Python2
- Kompilovanie Java riešení v dočasnom priečinku
- Informovanie o neúspešnom generovaní vstupov
- Sformátovaný a otypovaný kód
- Prepísané README
- Bugfixes

</details>

<details>
<summary>Nemergnuté zmeny</summary>

- `--best-only` prepínač pre tester
- **Zjednotený nástroj `itool`**
- **Okresané CLI parametre, BREAKING CHANGE**
- **Podpora starého formátu IDF**
- **Varovania pre dlhé behy a objemné vstupno-výstupné dáta**
- **Podpora MacOS**
- Rôzne malé vylepšenia, refaktorovanie, bugfixy
- **Rozšírená funkcionalita IDF o podporu YAML a `!eval`**
- **Poetry manager**
- Kontrola aktualizácií pri spustení generátora
- Podpora priečinka ako argument pre `itool generate` a `itool sample` &ndash; automatické načítanie IDF a zadania
- Automatický varovný timelimit tesných riešení
- **Možnosť výpisať výstup hodnotiča pri WA** (pomocou prepínača `-D`)
- **Kompilovanie do samostatného priečinku** `prog/` (zmena pomocou prepínača `--progdir`)
- Začaté písanie testov
- **Plne paralelné kompilovanie a testovanie**
- Generovanie vstupov predvolene pomocou `pypy3`
- Zmodernizovaný a zrefaktorovaný kód
- JSON výstup testera
- Bugfixes

</details>

## Rýchlokurz

```bash
# napíšeme si riešenia, generátor, idf a potom:
itool s . # priečinok so zadanie.md
itool g .
itool t .

# o pomoc požiadame `itool [podpríkaz] -h`, napríklad:
itool t -h
```

# `input-tool`

Nástroj, ktorý výrazne zjednodušuje vytváranie a testovanie vstupov pre súťažné programátorské príklady. Umožňuje automatizovane generovať vstupy, vytvárať vzorové výstupy, kompilovať a testovať riešenia, merať čas ich behu, ...

## Inštalácia

Na **Linuxe** a **MacOS** je to dosť jednoduché. Windows nie je podporovaný, ale pod **WSL** by to malo ísť bez problémov.

### Prerekvizity:

- Na **Windows** `input-tool` funguje iba pod **WSL**
  <details>
  <summary>Inštalácia WSL</summary>

  ```powershell
  # spustite Powershell ako administátor (pravý klik na ikonu a "Run as administrator")
  wsl --install # nainštaluje WSL
  # reštartujte počítač
  # znovu otvorte Powershell
  wsl           # spustí WSL
  # pokračujte ako na Ubuntu
  ```

  </details>

- Na **MacOS** potrebujete nainštalovať `coreutils` a `gcc`
  - všetko potrebné získate napríklad pomocou `brew install coreutils gcc make python3`
- Potrebujete `python3` ($\geq 3.8$) a `make`
- Potrebujete kompilátory C/C++ (`gcc/clang/...`), Pascalu (`fpc`), Javy, Rustu (`rustc`) &ndash; samozrejme iba pre jazyky ktoré plánujete spúštať
- _Nepovinne_ `time` (Linux) / `gnu-time` (MacOS) (nestačí bashová funkcia) ak chceme _Real/User/System_ časy

### Inštalácia na Ubuntu

```bash
# nainštalujeme prerekvizity
sudo apt update
sudo apt install gcc g++ make python3 python3-pip pipx
pipx ensurepath
# nainštalujeme input-tool
pipx install input-tool
# neskôr môžeme aktualizovať
pipx upgrade input-tool
```

<details>
<summary>Rôzne spôsoby inštalácie</summary>

```bash
# pomocou pipx
pipx install input-tool
# aktualizujeme podobne
pipx upgrade input-tool

# pomocou pip
pip3 install --break-system-packages input-tool
# aktualizujeme podobne
pip3 install -U --break-system-packages input-tool

# inštalácia z Githubu namiesto PyPi
pipx install git+https://github.com/fezjo/input-tool.git
# alebo
git clone https://github.com/fezjo/input-tool.git
cd input-tool
pipx install -e .
```

</details>

### Problémy na Windows WSL

Často sa stáva, že program pod WSL beží oveľa pomalšie ako na Linuxe (dostáva TLE), konkrétne pri programoch s veľkým vstupom/výstupom. Toto sa deje ak WSL musí pracovať so súborovým systémom Windowsu. Riešenie je presunúť priečinok v ktorom pripravujeme úlohu do WSL (teda `/home/username/...` namiesto `/mnt/c/...`).

# `itool`

Všetky príkazy sú dostupné pod jedným príkazom `itool`. Tento príkaz má niekoľko podpríkazov, ktoré sa dajú spustiť pomocou `itool <subcommand>`. Tieto podpríkazy sú:

- `generate` (alebo `g`)
- `sample` (alebo `s`)
- `test` (alebo `t`)
- `compile` (alebo `c`), `colortest`, `checkupdates`

# `itool sample`

Tento skript dostane na vstupe (alebo ako argument) zadanie príkladu. Vyrobí (defaultne v priečinku `./test`) sample vstupy a sample výstupy pre tento príklad.

Defaultne pomenúva súbory `00.sample.in` resp. `00.sample.x.in`, ak je ich viac. Viete mu povedať, aby pomenúval vstupy inak, napr. `0.sample.in`, alebo `00.sample.a.in` aj keď je len jeden vstup. Dá sa nastaviť priečinok, kde sa vstupy a výstupy zjavia, a tiež prípony týchto súborov.

Príklady použitia:

```bash
itool sample -h
itool sample prikl1.md
itool sample --batchname 0.sample < cesta/k/zadaniam/prikl2.md
```

# `itool generate`

1. Najskôr treba nakódiť **generátor**, ktorý nazvite `gen` (teda napr. `gen.cpp` alebo `gen.py`).
2. Následne vytvoríte **IDF**, vysvetlené nižšie.
3. Spustíte generátor pomocou `itool generate idf` a tešíte sa.

## Generátor

Názov generátoru sa začína `gen` (napríklad `gen.cpp`). Generátor je program, ktorý berie na vstupe jeden riadok (kde dáte čo chcete, napríklad dve čísla, maximálne $n$ a $m$.) Tento program vypíše, normálne na `stdout`, jeden vstup úlohy.

Dávajte si pozor, aby bol vypísaný vstup korektný, žiadne medzery na koncoch riadkov, dodržujte limity, čo sľubujete v zadaní (toto všetko vieme automatizovane zaručiť s pomocou validátora). Jedna z vecí, čo je dobré robiť, je generovať viacero typov vstupov. (Povedzme náhodné čísla, veľa clustrov rovnakých, samé párne lebo vtedy je bruteforce pomalý, atď.) To je dobré riešiť tak, že jedno z čísel, čo generátor dostane na vstupe je typ, podľa ktorého sa rozhodne, čo vygeneruje.

```bash
# Odporúčané je použiť základný tvar:
itool generate .
```

## IDF

IDF (Input Description File) je súbor, ktorý popisuje, ako vyzerajú sady a vstupy. Jeden riadok IDF slúži na vyrobenie jedného vstupu (až na špeciálne riadky). Každý takýto riadok poslúži ako vstup pre generátor a to, čo generátor vypľuje sa uloží do správneho súboru, napr. `02.a.in`. Čiže do IDF chcete obvykle písať veci ako maximálne $n$ (alebo aj presné $n$), typ vstupu, počet hrán grafu, atď., ale to už je na generátori aby sa rozhodol, čo s tými číslami spraví.

Sady v IDF oddeľujeme práznymi riadkami. Sady sú číslované `1..9`, ak je ich napr. `20`, tak `01..20`. Vstupy v jednej sade sú postupne písmenkované `a-z` (ak je ich veľa, tak sa použije viac písmen).

Príklad IDF

```r
# id pocet_vrcholov pocet_hran pocet_hracov
# 1. sada
{id} 10 1000 1
{id} 20 1000 2
{id} 30 1000 3

# 2.sada
$ hran: !eval 1e6
{id} 1000 {hran} 1
{id} 1000 {hran} 2
```

Vyrobí postupne vstupy `1.a.in`, `1.b.in`, `1.c.in`, `2.a.in`, `2.b.in`.

**Ak chcete niečim inicializovať `seed` vo svojom generátore, tak rozumný nápad je `{id}`**, pretože to je deterministické a zároveň unikátne pre každý vstup. Deterministické vstupy majú výhodu, že ak niekto iný pustí `itool generate` s rovnakými parametrami a rovnakým IDF, dostane rovnaké vstupy.

Najlepší jazyk na zvýraznenie IDF je _R_ alebo _Perl_ -- má rovnaké komentáre a zvýrazňuje `{}` a `!eval`.

# `itool test`

Cieľom tohto skriptu je otestovať všetky riešenia na vstupoch, overiť, či dávajú správne výstupy, zmerať čas behu a podobne.

**Pozor**, slúži to len na domáce testovanie, netestujte tým nejaké reálne kontesty, kde môžu užívatelia submitovať čo chcú. Nemá to totiž žiaden sandbox ani žiadnu ochranu pred neprajníkmi.

`itool test` sa používa veľmi jednoducho. Iba spustíte `itool test <zoznam riešení>` a ono to porobí všetko samé.

Odporúčame mať na konci `.bashrc` alebo pri spustení terminálu nastaviť kompilátory podobne ako sú na testovači, teda napríklad `export CXXFLAGS="-O2 -std=gnu++11 -Wno-unused-result -DDG=1"`, avšak `itool test` má nastavené rozumné predvolené hodnoty.

Riešenia pomenúvame s prefixom '`sol`' štýlom `sol-<hodnotenie>-<autor>-<algoritmus>-<zlozitost>.<pripona>`. Teda názov má podmnožinu týchto častí v tomto poradí, teda napríklad `sol-75-fero-zametanie-n2.cpp` alebo `sol-100-dezo.py`. Validátor má prefix '`val`', prípadný hodnotič '`check`'.

### Generovanie výstupov

Ak ešte neexistuje vzorový výstup ku nejakému vstupu (teda napríklad ste práve vygenerovali vstupy), použije sa prvý program na jeho vygenerovanie. Ostatné programy porovnávajú svoje výstupy s týmto.

Dôležité je, aby program, ktorý generuje výstupy zbehol na všetkých vstupoch správne. Pokial by sa niekde zrúbal/vyTLEl, tak môžu byť výstupy pošahané.

## Užitočné prepínače

### `-t --time`

Neoptimálne riešenia by často bežali zbytočne dlho, ak vôbec aj dobehli. Tento argument nastaví časový limit v sekundách. Vie to byť desatinné číslo. Vie to byť rôzne pre jednotlivé jazyky. Napríklad `-t 1`, `t -0.5` alebo `-t "3,cpp=1,py=5"`.

### `-F --no-fail-skip`

Štandardne sa programy, ktoré na niektorom vstupe zlyhali nevyhodnocujú na zvyšných testov v danej sade. Takto to funguje na niektorých súťažiach a urýchľuje to testovanie napríklad bruteforcov. Často však takéto správanie necheme a preto ho môžeme týmto argumentom vypnúť.

### `-R --Reset`

Už existujú výstupy ale sú zlé? `-R` prepíše výstupy nanovo tým, čo vyrobí prvý program.

### `-d --diff`

Niektoré úlohy potrebujú na určenie správnosti hodnotič. Ten vie byť automaticky určený ak ako argument uvedieme priečinok v ktorom sa nachádza a hodnotič má štandardné meno. Ak tieto podmienky nie sú splnené, vieme ho manuálne určiť pomocou tohoto argumentu, napríklad `-d checker.py`.

### `-D --show-diff-output`

Ak je výsledkom testovania WA, vypíše sa skrátený výstup hodnotiča. Pri štandardnom `diff`e sa vypíše porovnanie riadkov vedľa seba.

### `--pythoncmd`

Niekedy by sme boli radi, keby Python nebol taký pomalý. To sa dá väčšinou vyriešiť použitím _PyPy_ interpretera. Dokážeme to určiť pomocou tohoto argumentu, použitím `--pythoncmd pypy3`.

### `-j --threads`

Kompilovanie, generovanie aj testovanie vieme značne urýchliť paralelizáciou. Tento argument určuje, koľko vlákien sa má použiť. Väčšinou existuje optimálny počet vlákien, ktorý je menší ako počet dostupných vlákien vášho procesoru. Odporúčame teda občas a hlavne pred zverejnením úloh pretestovať riešenia bez paralelizácie (`-j 1`).

### Príklady

```bash
# pomoc!
itool test -h
# najzákladnejšie použitie, keď máme všetko v aktuálnom priečinku
itool test .
# chceme spustiť iba vzorové riešenia
itool test sol-100*
# chceme vidieť na ktorých všetkých vstupoch programy nefungujú (nielen na ktorých
# sadách), chceme vidieť ako sa líšia od vzorového výstupu a robíme to sériovo
itool test -FD -j 1 .
# bežné použitie, ak si dáme všetky riešenia do priečinku `sols`
itool test -t "3,cpp=0.5,py=5" sols .
# ak požívame názvoslovie ktoré input-tool nevie dobre rozpoznať, môžeme najprv
# spustiť vzorové riešenie ktoré vygeneruje výstupy a následne použiť wildcardy
itool test -R vzorove-riesenie.py
itool test . vzor* ries* program2.cpp cokolvek.py
```

# Pokročilé

Ak chcete vedieť, aké cool veci navyše dokážu `itool generate` a `IDF`, prečítajte si o nich v súbore [`GENERATOR.md`](GENERATOR.md).

Ak chcete vedieť, aké cool veci navyše dokáže `itool test` a **ako písať validátor a hodnotič**, prečítajte si o tom v súbore [`TESTER.md`](TESTER.md).

# Feedback

Ak vám niečo nefunguje, alebo vám chýba nejaká funkcionalita, napíšte mi, prosím, mail alebo vyrobte issue.
