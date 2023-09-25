from test_utils import *

init(cwd="progdir")

result_gen = run("input-generator . -g cat")
print(result_gen.stdout.decode("utf-8"))

result_test = run("input-tester sol-a.cpp ./sol-b.cpp cdir/sol-c.cpp")
print(result_test.stdout.decode("utf-8"))

assert sorted(os.listdir("test/prog")) == ["sol-a", "sol-b", "sol-c"]

statistics = parse_statistics(result_test.stdout.decode("utf-8"))
assert len(statistics) == 3
assert all(map(lambda row: row[4] == "OK", statistics))

print("ALL GOOD")
