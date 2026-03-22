from pathlib import Path
import sys


def main() -> int:
    if len(sys.argv) != 2:
        return 2

    input_path = Path(sys.argv[1])
    for raw in input_path.read_text().splitlines():
        value = raw.strip()
        if not value:
            continue

        print(value, flush=True)
        response = sys.stdin.readline().strip()
        if response == "joker":
            continue
        if response == "":
            return 1
        if response != value:
            return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
