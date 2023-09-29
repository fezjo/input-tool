from test_utils import init, parse_statistics, run

init(cwd="timelimits")

result_gen = run("input-generator . -g cat")
print(result_gen.stdout.decode("utf-8"))

result_test = run("input-tester . -t '1,cpp=0.1'")
print(result_test.stdout.decode("utf-8"))

statistics = parse_statistics(result_test.stdout.decode("utf-8"))
assert {row[0]: row[4] for row in statistics} == {
    "sol.cpp": "OK",
    "sol-1.py": "OK",
    "sol-2.py": "OK",
    "sol-3.py": "tOK",
    "sol-4.py": "tOK",
    "sol-5.py": "tOK",
    "sol-10.py": "TLE",
}

print("ALL GOOD")
