# Integration Test Progress

Last updated: 2026-02-13

Status legend:
- `BEHAVIOR`: covered with behavioral assertions
- `SMOKE`: covered by exit-code-only CLI smoke tests
- `PLANNED`: not implemented yet, explicitly queued below

## Flag Coverage by Tool

### Root `itool`

| Flag / input       | Status | Notes              |
| ------------------ | ------ | ------------------ |
| `--help`           | SMOKE  | Exit code `0`      |
| `--version`        | SMOKE  | Exit code `0`      |
| invalid subcommand | SMOKE  | Exit code non-zero |

### `itool sample` / `itool s`

| Flag / input      | Status   | Notes                  |
| ----------------- | -------- | ---------------------- |
| `-h`, `--help`    | SMOKE    | CLI smoke              |
| `--help-all`      | SMOKE    | CLI smoke              |
| `--input DIR`     | PLANNED  |                        |
| `--output DIR`    | PLANNED  |                        |
| `--inext EXT`     | PLANNED  |                        |
| `--outext EXT`    | PLANNED  |                        |
| `--force-multi`   | BEHAVIOR | Writes `00.sample.a.*` |
| `--batch NAME`    | PLANNED  |                        |
| `--boring`        | PLANNED  |                        |
| `task` positional | BEHAVIOR | `task.md` extraction   |
| unknown flag      | SMOKE    | non-zero               |

### `itool generate` / `itool g`

| Flag / input             | Status   | Notes                                |
| ------------------------ | -------- | ------------------------------------ |
| `-h`, `--help`           | SMOKE    | CLI smoke                            |
| `--help-all`             | SMOKE    | CLI smoke                            |
| `--no-update-check`      | PLANNED  |                                      |
| `--input DIR`            | PLANNED  |                                      |
| `--progdir DIR`          | PLANNED  |                                      |
| `--inext EXT`            | PLANNED  |                                      |
| `--no-compile`           | PLANNED  |                                      |
| `--execute`              | PLANNED  |                                      |
| `--boring`               | PLANNED  |                                      |
| `-q`, `--quiet`          | PLANNED  |                                      |
| `--keep-inputs`          | PLANNED  |                                      |
| `--clear-bin`            | PLANNED  |                                      |
| `-g`, `--gen`            | BEHAVIOR | `cat`-based deterministic generation |
| `--idf-version`          | BEHAVIOR | v1/v2 + invalid config path          |
| `--pythoncmd CMD`        | PLANNED  |                                      |
| `-j`, `--threads`        | PLANNED  |                                      |
| `description` positional | BEHAVIOR | `idf` file and directory autodetect  |
| unknown flag             | SMOKE    | non-zero                             |

### `itool test` / `itool t`

| Flag / input             | Status   | Notes                              |
| ------------------------ | -------- | ---------------------------------- |
| `-h`, `--help`           | SMOKE    | CLI smoke                          |
| `--help-all`             | SMOKE    | CLI smoke                          |
| `--input DIR`            | BEHAVIOR | missing-dir failure path covered   |
| `--output DIR`           | PLANNED  |                                    |
| `--progdir DIR`          | PLANNED  |                                    |
| `--inext EXT`            | PLANNED  |                                    |
| `--outext EXT`           | PLANNED  |                                    |
| `--tempext EXT`          | PLANNED  |                                    |
| `--no-compile`           | PLANNED  |                                    |
| `-S`, `--no-sort`        | BEHAVIOR | explicit order preserved           |
| `--dupprog`              | BEHAVIOR | duplicate solutions retained       |
| `--best-only`            | BEHAVIOR | best solution + validator behavior |
| `--execute`              | PLANNED  |                                    |
| `--boring`               | PLANNED  |                                    |
| `-q`, `--quiet`          | PLANNED  |                                    |
| `--no-statistics`        | BEHAVIOR | summary table hidden               |
| `--json FILE`            | BEHAVIOR | used as primary assertion oracle   |
| `--keep-temp`            | BEHAVIOR | temp files retained                |
| `--clear-bin`            | PLANNED  |                                    |
| `-R`, `--Reset`          | BEHAVIOR | recompute outputs                  |
| `--rustime`              | PLANNED  |                                    |
| `-t`, `--time`           | BEHAVIOR | status/timelimit semantics         |
| `--wtime`                | PLANNED  |                                    |
| `-m`, `--memory`         | PLANNED  |                                    |
| `-d`, `--diff`           | BEHAVIOR | `diff` and `check.py` paths        |
| `-D`, `--show-diff`      | BEHAVIOR | side-by-side diff assertions       |
| `-F`, `--no-fail-skip`   | BEHAVIOR | fail-skip toggling                 |
| `--ioram`                | PLANNED  |                                    |
| `--pythoncmd CMD`        | PLANNED  |                                    |
| `-j`, `--threads`        | BEHAVIOR | deterministic serial runs          |
| `programs...` positional | BEHAVIOR | file and directory forms           |
| unknown flag             | SMOKE    | non-zero                           |

### `itool compile` / `itool c`

| Flag / input             | Status   | Notes                       |
| ------------------------ | -------- | --------------------------- |
| `-h`, `--help`           | SMOKE    | CLI smoke                   |
| `--help-all`             | SMOKE    | CLI smoke                   |
| `--progdir DIR`          | PLANNED  |                             |
| `--boring`               | PLANNED  |                             |
| `-q`, `--quiet`          | PLANNED  |                             |
| `--pythoncmd CMD`        | PLANNED  |                             |
| `-j`, `--threads`        | BEHAVIOR | compile success/failure     |
| `programs...` positional | BEHAVIOR | multiple and invalid source |
| unknown flag             | SMOKE    | non-zero                    |

### `itool autogenerate` / `itool ag`

| Flag / input             | Status   | Notes                          |
| ------------------------ | -------- | ------------------------------ |
| `-h`, `--help`           | SMOKE    | CLI smoke                      |
| `--help-all`             | SMOKE    | CLI smoke                      |
| `--input DIR`            | PLANNED  |                                |
| `--output DIR`           | PLANNED  |                                |
| `--progdir DIR`          | PLANNED  |                                |
| `--inext EXT`            | PLANNED  |                                |
| `--outext EXT`           | PLANNED  |                                |
| `--tempext EXT`          | PLANNED  |                                |
| `--no-compile`           | PLANNED  |                                |
| `--execute`              | PLANNED  |                                |
| `--boring`               | PLANNED  |                                |
| `-q`, `--quiet`          | PLANNED  |                                |
| `--no-statistics`        | PLANNED  |                                |
| `--json FILE`            | BEHAVIOR | output assertions              |
| `--keep-inputs`          | PLANNED  |                                |
| `--keep-temp`            | PLANNED  |                                |
| `--clear-bin`            | PLANNED  |                                |
| `-g`, `--gen`            | BEHAVIOR | deterministic generation       |
| `--idf-version`          | PLANNED  |                                |
| `--pythoncmd CMD`        | PLANNED  |                                |
| `-j`, `--threads`        | BEHAVIOR | deterministic serial run       |
| `description` positional | BEHAVIOR | directory/idf handling         |
| `programs...` positional | BEHAVIOR | best-only tested solution path |
| unknown flag             | SMOKE    | non-zero                       |

### `itool colortest`

| Flag / input   | Status | Notes     |
| -------------- | ------ | --------- |
| `-h`, `--help` | SMOKE  | CLI smoke |
| unknown flag   | SMOKE  | non-zero  |

### `itool checkupdates`

| Flag / input   | Status | Notes     |
| -------------- | ------ | --------- |
| `-h`, `--help` | SMOKE  | CLI smoke |

## Existing Tests (Implemented)

### `tests/test_cli_integration.py`
- `test_cli_flags_exit_zero`
- `test_cli_flags_exit_nonzero`

### `tests/test_tester_integration.py`
- `test_timelimit_language_matrix_statuses`
- `test_best_only_selects_single_solution`
- `test_side_by_side_diff_and_statuses`
- `test_statistics_table_shape`
- `test_default_fail_skip_skips_remaining_tests_in_batch`
- `test_no_fail_skip_runs_remaining_tests_in_batch`
- `test_outputs_are_reused_unless_reset_requested`
- `test_tester_fails_on_missing_input_directory`
- `test_tester_fails_on_unsupported_checker_format`
- `test_validator_reports_valid_status_when_inputs_pass`
- `test_validator_reports_exc_when_input_fails_validation`

### `tests/test_checker_integration.py`
- `test_explicit_diff_checker_matches_expected_wa`
- `test_check_checker_allows_approximate_float_comparisons`
- `test_check_checker_nonstandard_exit_code_reports_warning_and_marks_wa`

### `tests/test_tester_flags_integration.py`
- `test_keep_temp_preserves_temp_files`
- `test_default_temp_cleanup_removes_temp_files`
- `test_no_statistics_hides_summary_table`
- `test_checker_is_auto_detected_without_diff_flag`
- `test_tester_fails_when_multiple_checkers_found`

### `tests/test_tester_selection_integration.py`
- `test_default_sort_prefers_better_scored_solution`
- `test_no_sort_preserves_user_program_order`
- `test_default_deduplicates_same_program_argument`
- `test_dupprog_keeps_duplicate_program_argument`
- `test_best_only_keeps_validator_and_best_solution`

### `tests/test_generator_idf_integration.py`
- `test_idf_v2_yaml_eval_merge_nofile_multiline_and_escape`
- `test_idf_v1_legacy_equals_commands_work`
- `test_idf_v2_rejects_nonboolean_nofile`
- `test_generate_directory_fails_when_multiple_idf_files_exist`

### `tests/test_sample_compile_integration.py`
- `test_sample_extracts_io_blocks_into_files`
- `test_sample_fails_on_mismatched_input_output_blocks`
- `test_compile_creates_binaries_for_valid_cpp_sources`
- `test_compile_fails_for_invalid_cpp_source`

### `tests/test_autogenerate_integration.py`
- `test_autogenerate_generates_and_tests_best_solution_only`
- `test_autogenerate_fails_with_multiple_idf_candidates`

## Planned Tests (Backlog)

### Planned for `test` command
- `test_tester_wtime_marks_t_statuses`
- `test_tester_memorylimit_triggers_failure`
- `test_tester_rustime_prints_rus_columns`
- `test_tester_ioram_executes_in_ramdisk`
- `test_tester_no_compile_requires_prebuilt_binary`
- `test_tester_execute_treats_program_as_shell_command`
- `test_tester_pythoncmd_override_is_used`
- `test_tester_custom_output_dir_and_extensions`
- `test_tester_clear_bin_removes_compiled_artifacts`
- `test_tester_progdir_override_compiles_to_custom_dir`

### Planned for `generate` command
- `test_generate_no_update_check_suppresses_update_probe`
- `test_generate_custom_input_dir_and_extension`
- `test_generate_keep_inputs_preserves_existing_files`
- `test_generate_clear_bin_removes_generator_binaries`
- `test_generate_no_compile_requires_executable_generator`
- `test_generate_execute_runs_generator_as_command`
- `test_generate_pythoncmd_override_is_used`
- `test_generate_threads_parallel_generation`
- `test_generate_progdir_override_compiles_to_custom_dir`

### Planned for `sample` command
- `test_sample_custom_input_output_dirs`
- `test_sample_custom_extensions`
- `test_sample_custom_batch_name`
- `test_sample_directory_task_autodetects_zadanie_md`
- `test_sample_boring_disables_colors`

### Planned for `compile` command
- `test_compile_progdir_override`
- `test_compile_quiet_suppresses_subprogram_output`
- `test_compile_pythoncmd_override_for_python_targets`
- `test_compile_boring_disables_colors`

### Planned for `autogenerate` command
- `test_autogenerate_custom_dirs_and_extensions`
- `test_autogenerate_no_statistics_hides_summary`
- `test_autogenerate_keep_inputs_preserves_existing_files`
- `test_autogenerate_keep_temp_preserves_temp_files`
- `test_autogenerate_clear_bin_removes_artifacts`
- `test_autogenerate_idf_version_switch`
- `test_autogenerate_pythoncmd_override`
- `test_autogenerate_no_compile_requires_prebuilt_programs`
- `test_autogenerate_execute_mode`
- `test_autogenerate_progdir_override`

### Planned for output rendering contract
- `test_statistics_table_header_contract`
- `test_statistics_table_row_alignment_contract`
- `test_statistics_table_batch_letters_contract`
- `test_json_normalized_snapshot_contract`

## Current totals
- Implemented tests: 55
- Planned tests in backlog: 40
