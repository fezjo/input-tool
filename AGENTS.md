# input-tool

CLI tool for creating and testing inputs for competitive programming contests. The main entry point is `itool`, which dispatches to subcommands.

## Subcommands

| Command | Alias | Module | Purpose |
|---|---|---|---|
| `sample` | `s` | `input_sample.py` | Extract sample I/O blocks from task statement (`zadanie.md` or specified `.md`) |
| `generate` | `g` | `input_generator.py` | Compile generator and produce `.in` files from IDF |
| `test` | `t` | `input_tester.py` | Compile solutions and run them against generated inputs |
| `autogenerate` | `ag` | — | Combined generate + test |
| `findlimits` | `fl` | `input_findlimits.py` | Binary-search for time/memory limits |

## Key Concepts

**IDF (Input Description File):** Named `idf`, lives in the task directory. Each non-comment line is fed as stdin to the generator; stdout becomes a test input file. Batch number and letter are derived from the IDF structure.

**Sample files:** Named `00.sample.a.in` / `00.sample.a.out`. Created by `itool s`, sourced from the statement (````vstup` / `vystup` blocks). The generator must never overwrite them.

**Generated test files:** Named `{batch}.{letter}.in` (e.g. `1.a.in`, `2.b.in`). Single-test batches produce `{batch}.in` without a letter.

**prog/ directory:** Default output for compiled binaries (configurable with `--progdir`). Recompilation is triggered when source `ctime > binary ctime`.

**Solution naming convention:** `sol-{score}-{author}-{algo}-{complexity}.cpp` — the tester reads metadata from the filename.

## Running Tests

```bash
uv run pytest                          # all tests
uv run pytest tests/test_generate_integration.py   # one file
uv run pytest tests/... -v             # verbose
```

Tests use `pytest-xdist` with `-n 4` workers by default (set in `pyproject.toml`).

## Test Utilities (`tests/test_utils.py`)

- `copy_fixture_tree(name, case_dir)` — copies `tests/fixtures/{name}/` to a temp dir, returns the path
- `run_itool(args, cwd, check=True, threads=1)` — runs `uv run itool ...`, captures stdout+stderr merged; automatically appends `--no-update-check` for `g`/`ag` and `--threads 1` for parallelizable commands
- `run_itool_json(args, cwd)` — like above but also parses JSON output file
- `parse_statistics(output)` — extracts the tester results table from stdout
- `get_input_files(dir)` — sorted list of `*.in` filenames in a directory
- `case_dir` fixture — pytest fixture that provides a temp dir and `chdir`s into it (required by all test functions as first arg)

## Fixture Structure (`tests/fixtures/`)

Each fixture is a directory containing a minimal task setup:

- `idf` — input description file
- `gen.cpp` / `gen.py` — generator source
- `sol-*.cpp` / `sol-*.py` — solution(s)
- `task.md` — task statement with sample blocks (for `itool s` fixtures)
- `test/` — pre-existing test files (if needed)

Fixture naming conventions: `generate_*`, `autogen_*`, `checker_*`, `sample_*`, `findlimits_*`, `lang_matrix*`.

## Common Gotchas

- `itool g` with a single IDF line produces `1.in`; two lines produce `1.a.in` + `1.b.in`.
- Sample file preservation: the cleanup in `input_generator.py:setup_indir` skips any file with `"sample"` in its name — both `.in` and `.out`.
- `run_itool` defaults to `threads=1` to keep tests deterministic; pass `threads=None` to use the system default.
- The `--force-multi` flag on `itool s` forces the `00.sample.a.*` naming even with a single sample.
