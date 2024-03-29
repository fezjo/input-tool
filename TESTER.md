# Tester

### Užitočné prepínače

```
itool test:
  -h, --help
    show this help message and exit
  --help-all
    show help message with all the available options and exit
  -q, --quiet
    dont let subprograms print stuff
  -R, --Reset
    recompute outputs
  -t TIMELIMIT, --time TIMELIMIT
    set timelimit, 0 means unlimited and can be set in per language format (default: 3,cpp=1,py=5)
  -d, --diff
    program which checks correctness of output [format: `diff $our $theirs`, `check $inp $our $theirs`, details in TESTER.MD] (default: diff)
  -D, --show-diff-output
    show shortened diff output on WA
  -F, --no-fail-skip
    dont skip the rest of input files in the same batch after first fail
  --pythoncmd
    what command is used to execute python, e.g. `python3` or `pypy3` (default: python3)
  -j THREADS, --threads THREADS
    how many threads to use (default: 1/4 of threads)
  --json JSON
    also write output in json format to file
```

### Paralelizácia

Pri testovaní viacero riešení naraz budú časy ktoré nameriame na jednotlivých riešeniach o kúsok väčšie ako tie pri sériovom testovaní. Odporúčame teda občas a hlavne pred zverejnením úloh pretestovať riešenia bez paralelizácie.

### Inteligencia

Nástroj sa snaží byť inteligentný. Na zoznam riešení mu vieme dať priečinok a nástroj sa v ňom pokúsi nájsť relevantné programy (`sol*`, `val*`, `check*`, ...). Ďalej sa pokúsi (magicky) utriediť riešenia od najlepšieho po najhoršie. Poradie má zmysel napríklad, keď sa generujú nové výstupy. Nakoniec sa nástroj pokúsi zistiť, ako ste tieto programy chceli spustiť.

Aby inteligencia správne fungovala, chceme dodržiavať nasledujúci štýl názvov súborov:

- `sol*`

  - vo všeobecnosti chceme použiť formát `sol-<hodnotenie>-<autor>-<algoritmus>-<zlozitost>.<pripona>`
  - teda napríklad `sol-75-fero-zametanie-n2.cpp` alebo `sol-100-dezo.py`

- `val*` - validátor
- `check*`, `diff*`, `test*` - hodnotiče

Triedenie potom vyzerá napríklad takto: `sol-vzor` = `sol-vzorak` > `sol` > `sol-100` > `sol-40` > `sol-4` > `sol-wa`.

Ďalej sa automaticky pokúsi zistiť, aký program ste chceli spustiť a prípadne skompiluje, čo treba skompilovať. Ak napríklad zadáte `sol-bf` pokúsi sa nájsť, či tam nie je nejaké `sol-bf.py`, `sol-bf.cpp` ... a pokúsi sa doplniť príponu. Tiež sa pokúsi určiť, ako ste program chceli spustiť, či `./sol.py` alebo `python3 sol.py`. Samozrejme, hádanie nie je dokonalé ale zatiaľ skústenosti ukazujú, že funguje dosť dobre.

Inteligencia sa dá vypnúť pomocou `--no-sort` (triedenie), `--no-compile` (kompilácia), `--execute` (celé automatické rozoznávanie).

### Validátor

Riešenie, ktoré sa začína `val` je považované za validátor. Validátor je program, ktorý na `stdin` dostane vstup a zrúbe sa (`exit 1`), ak vstup nebol správny. Na `stderr` môžete vypísať nejakú krátku správu, že čo bolo zle, na `stdout` radšej nič nepíšte. Pokiaľ nerobíte zveriny, tak sa `stdout` v podstate zahodí.

Validátor navyše dostane ako argumenty názov vstupného súboru rozsekaný podľa bodky. Príklad: `./validator 00 sample a in < 00.sample.a.in`. Tieto argumenty môžete odignorovať, alebo využiť, a napríklad kontrolovať, že ak je číslo sady `01`, tak vstup má byť do 100, ak je číslo sady `02`, vstup má byť do 1000.

### Hodnotič / Checker

Správnosť výstupu sa nehodnotí tak, že ho len porovnáme so vzorovým? Treba checker? Nie je problém.

Hodnotič vie byť automaticky určený ak ako argument uvedieme priečinok v ktorom sa nachádza a hodnotič má štandardné meno, alebo ho vieme manuálne určiť pomocou `-d <program>`.

Podporujeme viacero typov hodnotičov, ktoré ako argumenty berú názvy súborov a budú spúštané vo formáte:

- `diff out_vzor out_test`
- `check inp out_vzor out_test`
- `ch_ito inp out_test out_vzor`
- `test dir name inp out_vzor out_test`

### Zobrazovanie

- Na konci sa zobrazí pekná tabuľka so zhrnutím (vypnete pomocou `--no-statistics`):
  - Časy behov riešenia zo sád ktoré nedostali `OK` sa nezapočítavajú
  - Validátor môže mať status `OK` alebo `VALID`
  - Riešenie môže mať status `OK`, `WA`, `EXC`, `TLE`
  - Ak majú pred sebou `t` (napríklad `tOK`), znamená to, že riešenie tento výsledok dostalo po prekročení varovného (tesného) časového limitu (`--wtime` = predvolene tretina časového limitu)
  - _Chceli by sme aby vzorové riešenie dostalo čisté `OK`, nech menej vyladené programy riešiteľov stále prejdú v časovom limite_
- Bežne sa výsledky zobrazujú farebne, dá sa to aj vypnúť (`--boring`).
- Tiež pokiaľ vás otravujú veci, čo vypisujú kompilátory a programy na stderr a podobne, dá sa to schovať pomocou `--quiet`.
- Ak máme na počítači nainštalovaný `time`, beh programov sa meria aj jednotlivo pre _Real/User/System_ čas a tento údaj vieme zobraziť pre každý beh (zapneme pomocou `--rustime`)
