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

import json
import os
import subprocess
from typing import Sequence
from input_tool.common.commands import Langs
from input_tool.common.programs.solution import Solution
from input_tool.common.programs.validator import Validator
from input_tool.common.tools_common import setup_config
from input_tool.input_tester import (
    parse_args,
    get_relevant_prog_files_deeper,
    create_programs_from_files,
)


def find_best_solutions(candidates: Sequence[str]) -> dict[Langs.Lang, str]:
    files = get_relevant_prog_files_deeper(candidates)
    solutions, _checker_files = create_programs_from_files(files, True)
    solutions.sort()
    res = {}
    for solution in solutions:
        if (
            isinstance(solution, Solution)
            and not isinstance(solution, Validator)
            and solution.lang is not Langs.Lang.unknown
            and solution.lang not in res
        ):
            res[solution.lang] = solution.name
    return res


def find_timelimits_lowerbound(
    solutions: dict[Langs.Lang, str]
) -> dict[Langs.Lang, float]:
    json_file = "stats.json"
    command = ["input-tester", "-t", "0", "--json", json_file, *solutions.values()]
    subprocess.run(command)
    with open(json_file, "r") as f:
        stats = json.load(f)
    # os.remove(json_file)
    res = {}
    for sol_stat in stats:
        name = sol_stat["name"]
        lang = next(lang for lang, sol in solutions.items() if sol == name)
        res[lang] = sol_stat["maxtime"]
    return res

def run_all(timelimit_lowerbound: dict[Langs.Lang, float]) -> dict:
    timelimit_upperbound = {lang: max(1000, t * 15) for lang, t in timelimit_lowerbound.items()}
    timelimit_str = ",".join(f"{lang}={t / 1000}" for lang, t in timelimit_upperbound.items())
    print(timelimit_lowerbound)
    print(timelimit_upperbound)
    print(timelimit_str)
    json_file = "stats.json"
    command = ["input-tester", "-t", timelimit_str, "--json", json_file, "."]
    subprocess.run(command)
    with open(json_file, "r") as f:
        stats = json.load(f)
    # os.remove(json_file)
    return stats

OUTPUT = """
[{"name": "val.cpp", "maxtime": 104, "sumtime": 1356, "points": "", "result":
"VALID", "batchresults": {"00.sample": "OK", "1": "OK", "2": "OK", "3": "OK",
"4": "OK", "5": "OK", "6": "OK", "7": "OK", "8": "OK"}, "times": {"00.sample":
[[2], [3]], "1": [[2], [2], [3], [2], [2]], "2": [[3], [3], [3], [3], [3]], "3":
[[4], [4], [4], [4], [4]], "4": [[6], [15], [10], [7], [10]], "5": [[4], [12],
[27], [20], [24]], "6": [[36], [91], [91], [59], [92]], "7": [[48], [103],
[104], [60], [90]], "8": [[85], [90], [82], [57], [82]]}, "failedbatches": []},
{"name": "sol-8-points-vzorak-danza.cpp", "maxtime": 291, "sumtime": 3519,
"points": "8", "result": "OK", "batchresults": {"00.sample": "OK", "1": "OK",
"2": "OK", "3": "OK", "4": "OK", "5": "OK", "6": "OK", "7": "OK", "8": "OK"},
"times": {"00.sample": [[2], [3]], "1": [[2], [2], [2], [2], [2]], "2": [[3],
[3], [4], [3], [4]], "3": [[3], [5], [5], [4], [5]], "4": [[9], [29], [26],
[14], [28]], "5": [[5], [35], [38], [18], [33]], "6": [[72], [269], [278],
[157], [240]], "7": [[84], [283], [247], [157], [244]], "8": [[200], [291],
[278], [177], [253]]}, "failedbatches": []}, {"name":
"sol-8-points-vzorak-danza.py", "maxtime": 1758, "sumtime": 24022, "points":
"8", "result": "OK", "batchresults": {"00.sample": "OK", "1": "OK", "2": "OK",
"3": "OK", "4": "OK", "5": "OK", "6": "OK", "7": "OK", "8": "OK"}, "times":
{"00.sample": [[66], [65]], "1": [[68], [65], [68], [80], [62]], "2": [[70],
[77], [88], [84], [100]], "3": [[85], [93], [89], [92], [92]], "4": [[122],
[216], [231], [189], [213]], "5": [[88], [317], [264], [221], [206]], "6":
[[552], [1605], [1578], [1354], [1555]], "7": [[520], [1574], [1534], [1248],
[1550]], "8": [[1178], [1651], [1758], [1377], [1577]]}, "failedbatches": []},
{"name": "sol-8-fezjo-n.py", "maxtime": 1807, "sumtime": 25226, "points": "8",
"result": "OK", "batchresults": {"00.sample": "OK", "1": "OK", "2": "OK", "3":
"OK", "4": "OK", "5": "OK", "6": "OK", "7": "OK", "8": "OK"}, "times":
{"00.sample": [[60], [60]], "1": [[61], [66], [67], [63], [62]], "2": [[64],
[73], [77], [81], [78]], "3": [[84], [83], [86], [80], [96]], "4": [[110],
[221], [225], [197], [214]], "5": [[79], [240], [260], [244], [229]], "6":
[[531], [1666], [1684], [1571], [1678]], "7": [[523], [1662], [1620], [1480],
[1625]], "8": [[1234], [1637], [1807], [1571], [1677]]}, "failedbatches": []},
{"name": "sol-3-points-bf-n-squared-danza.cpp", "maxtime": 4707, "sumtime":
31657, "points": "5", "result": "TLE", "batchresults": {"00.sample": "OK", "1":
"OK", "2": "OK", "3": "OK", "4": "OK", "5": "OK", "6": "TLE", "7": "TLE", "8":
"TLE"}, "times": {"00.sample": [[3], [3]], "1": [[4], [3], [3], [4], [3]], "2":
[[3], [4], [4], [4], [3]], "3": [[4], [15], [18], [16], [14]], "4": [[249],
[3657], [3903], [3261], [3809]], "5": [[16], [3947], [4155], [4707], [3845]],
"6": [[21302]], "7": [[21302]], "8": [[21312]]}, "failedbatches": ["8", "6",
"7"]}, {"name": "sol-3-points-bf-n-squared-danza.py", "maxtime": 2239,
"sumtime": 9058, "points": "3", "result": "TLE", "batchresults": {"00.sample":
"OK", "1": "OK", "2": "OK", "3": "OK", "4": "TLE", "5": "TLE", "6": "TLE", "7":
"TLE", "8": "TLE"}, "times": {"00.sample": [[61], [64]], "1": [[59], [65], [61],
[60], [67]], "2": [[138], [146], [155], [142], [173]], "3": [[152], [1623],
[2067], [1786], [2239]], "4": [[21303]], "5": [[2296], [21303], [21303]], "6":
[[21304]], "7": [[21304]], "8": [[21305]]}, "failedbatches": ["5", "4", "6",
"7", "8"]}, {"name": "sol-3-points-bf-n-squared-optimized-danza.cpp", "maxtime":
5319, "sumtime": 33548, "points": "5", "result": "TLE", "batchresults":
{"00.sample": "OK", "1": "OK", "2": "OK", "3": "OK", "4": "OK", "5": "OK", "6":
"TLE", "7": "TLE", "8": "TLE"}, "times": {"00.sample": [[2], [4]], "1": [[3],
[2], [4], [3], [3]], "2": [[4], [4], [4], [4], [4]], "3": [[4], [18], [15],
[17], [18]], "4": [[241], [3665], [3905], [3343], [3960]], "5": [[17], [5319],
[4626], [4367], [3992]], "6": [[21302]], "7": [[21303]], "8": [[21308]]},
"failedbatches": ["8", "6", "7"]}, {"name": "sol-2-fezjo-n3.py", "maxtime":
2789, "sumtime": 11914, "points": "2", "result": "TLE", "batchresults":
{"00.sample": "OK", "1": "OK", "2": "OK", "3": "TLE", "4": "TLE", "5": "TLE",
"6": "TLE", "7": "TLE", "8": "TLE"}, "times": {"00.sample": [[63], [59]], "1":
[[66], [61], [67], [63], [66]], "2": [[1941], [2051], [2786], [1902], [2789]],
"3": [[2224], [21303], [21303]], "4": [[21303]], "5": [[21303], [21303]], "6":
[[21304], [21306]], "7": [[21304], [21305]], "8": [[21306], [21306]]},
"failedbatches": ["8", "3", "5", "4", "6", "7"]}, {"name":
"sol-2-points-bf-n-cubed-danza.cpp", "maxtime": 12838, "sumtime": 44972,
"points": "3", "result": "TLE", "batchresults": {"00.sample": "OK", "1": "OK",
"2": "OK", "3": "tOK", "4": "TLE", "5": "TLE", "6": "TLE", "7": "TLE", "8":
"TLE"}, "times": {"00.sample": [[2], [3]], "1": [[3], [3], [3], [3], [2]], "2":
[[75], [86], [103], [87], [117]], "3": [[99], [8245], [12684], [10619],
[12838]], "4": [[21302]], "5": [[14835], [21303], [21302]], "6": [[21303],
[21303]], "7": [[21302], [21303]], "8": [[21303], [21303]]}, "failedbatches":
["5", "4", "6", "7", "8"]}, {"name": "sol-1-point-bf-n-cubed-danza.py",
"maxtime": 90, "sumtime": 516, "points": "1", "result": "TLE", "batchresults":
{"00.sample": "OK", "1": "OK", "2": "TLE", "3": "TLE", "4": "TLE", "5": "TLE",
"6": "TLE", "7": "TLE", "8": "TLE"}, "times": {"00.sample": [[58], [61]], "1":
[[68], [81], [80], [90], [78]], "2": [[18171], [19188], [21303], [18360],
[21303]], "3": [[19216], [21303], [21302]], "4": [[21303], [21304]], "5":
[[21303]], "6": [[21305], [21306]], "7": [[21305], [21306]], "8": [[21307],
[21306]]}, "failedbatches": ["8", "3", "5", "4", "6", "2", "7"]}]
"""

def calculate_best_timelimit(stats: dict) -> dict[Langs.Lang, float]:
    for sol_stat in stats:
        name = sol_stat["name"]
        lang = Langs.from_ext(name.rsplit(".", 1)[1])
        print(name, lang, sol_stat["maxtime"], sol_stat["points"])
    return {}

def main():
    # args = parse_args()
    # setup_config(
    #     args,
    #     (
    #         "progdir",
    #         "pythoncmd",
    #         "fskip",
    #         "memorylimit",
    #         "quiet",
    #         "compile",
    #         "execute",
    #     ),
    # )
    # candidates = "."  # TODO
    # solutions = find_best_solutions(candidates)
    # timelimits = find_timelimits_lowerbound(solutions)
    # print(timelimits)
    # stats = run_all(timelimits)
    # print(stats)
    stats = json.loads(OUTPUT)
    best_timelimits = calculate_best_timelimit(stats)
    print(best_timelimits)

if __name__ == "__main__":
    main()