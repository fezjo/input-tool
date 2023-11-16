#!/usr/bin/env python3
# © 2023 fezjo
# Complex script that simplifies sequential usage of other scripts.

options = [
# input-sample
    "task",
# input-generator
    "gencmd",
    "pythoncmd_gen",
    "threads_gen",
    "clearbin",
    "description",
# input-tester
    "reset",
    "timelimit",
    "warntimelimit",
    "diffcmd",
    "quiet",
    "clearbin",
    "programs",
    "fskip",
    "pythoncmd_test",
    "threads_test",
# input-review
    # -a sample, generator, tester vzorak
    # -A -a + tester vsetky
    # --ct compute timelimit
]

# input-review -a
# input-review -A -t "1,
# input-review -A --ct
# input-review -A -g gen.py
# input-review -A -d check.py --ct

# input-sample ../zadanie.md
# input-sample ..
# input-generator .
# input-tester sol-vzorak.cpp
# input-tester -t "cpp=0.5,py=3" .
# input-tester .

# input-tool s ..
# input-tool g .
# input-tool t -G .
# input-tool t -t "cpp=0.5,py=3" .
# input-tool s .. g . t -G == input-tool r -a

# input-tool r -A --ct

# sol-4-tle-autor-cas.py  1.5s  AC  7s TLE
# sol-8-ok-fezjo.py       0.02s AC  1s AC
# res: 4s

