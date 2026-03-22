import sys
from pathlib import Path


def main() -> int:
    if len(sys.argv) != 6:
        return 2

    _batch = sys.argv[1]
    test = sys.argv[2]
    fifo_in = Path(sys.argv[3])
    fifo_out = Path(sys.argv[4])
    result_file = Path(sys.argv[5])

    test_path = Path("test") / f"{test}.in"
    numbers = [x.strip() for x in test_path.read_text().splitlines() if x.strip()]

    verdict = "OK"
    with (
        open(fifo_in, "w", buffering=1) as to_solution,
        open(fifo_out, "r") as from_solution,
    ):
        for raw in numbers:
            to_solution.write(raw + "\n")
            response = from_solution.readline()
            if response == "":
                verdict = "PRV"
                break
            if response.strip() != raw:
                verdict = "WA"
                break

    score = 1.0 if verdict == "OK" else 0.0
    result_file.write_text(f"{verdict}\n{score}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
