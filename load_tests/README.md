# BOOML Load Tests

Standalone load tests for an isolated BOOML staging environment. The tests use
Python, `requests`, and `ThreadPoolExecutor`; no production API endpoints are
changed.

## 1. Seed Data

Run this inside the backend container or any environment with Django settings:

```bash
python manage.py seed_load_test_data \
  --run-id smoke01 \
  --users 20 \
  --answer-rows 1000 \
  --create-contest
```

The command prints JSON with user names, problem ids, course id, and optional
contest id. Use the `fast_problem.id` for high-volume checks and `real_problem.id`
for lower-volume real checker checks.

Default password for seeded users is:

```text
LoadTestPass123!
```

Override it with `--password` and pass the same value to load-test commands with
`--password` or `BOOML_LOAD_PASSWORD`.

## 2. Run Scenarios

Set the target host:

```bash
export BOOML_BASE_URL=http://staging.example.test
```

From the repo root (`booml/`):

```bash
python -m load_tests.booml_load submissions-burst \
  --run-id smoke01 \
  --problem-id 123 \
  --users 20 \
  --submissions 1000 \
  --concurrency 50 \
  --csv-rows 1000 \
  --drain-timeout 600
```

Sustained submissions:

```bash
python -m load_tests.booml_load submissions-sustained \
  --run-id smoke01 \
  --problem-id 123 \
  --users 20 \
  --duration 600 \
  --rps 5 \
  --concurrency 50
```

Heavy CSV pre-validation:

```bash
python -m load_tests.booml_load heavy-csv \
  --run-id smoke01 \
  --problem-id 123 \
  --sizes-mb 1,10,50 \
  --drain-timeout 600
```

For accepted `csv_match` final statuses, seed `--answer-rows` must match the
submitted `--csv-rows`. Size-based CSV payloads keep the requested row count and
inflate cell values, so they are valid for pre-validation pressure; `csv_match`
may still fail at the checker stage because values intentionally differ from the
seeded answer file.

Mass polygon draft creation:

```bash
python -m load_tests.booml_load polygon-drafts \
  --run-id smoke01 \
  --problems 1000 \
  --concurrency 50
```

Full polygon lifecycle:

```bash
python -m load_tests.booml_load polygon-lifecycle \
  --run-id smoke01 \
  --problems 100 \
  --concurrency 10 \
  --csv-rows 1000
```

Very large polygon uploads:

```bash
python -m load_tests.booml_load polygon-large-uploads \
  --run-id smoke01 \
  --problems 5 \
  --upload-concurrency 2 \
  --polygon-file-size-mb 50 \
  --fields train_file,test_file,sample_submission_file,answer_file
```

All commands print JSON with throughput, status-code distribution, latency
percentiles, error samples, and scenario-specific acceptance checks.

## 3. Summarize DB State

Run after a load test:

```bash
python manage.py summarize_load_test --run-id smoke01
```

This reports:

- created load-test problems
- submission status counts
- active/zombie submissions
- missing pre-validation rows
- report count
- missing submission/problem files

## 4. Cleanup

Every load-test run must be cleaned by `run_id`. First inspect what will be
removed:

```bash
python manage.py cleanup_load_test_data --run-id smoke01
```

Then delete DB rows and uploaded files:

```bash
python manage.py cleanup_load_test_data --run-id smoke01 --yes
```

The cleanup command matches:

- users named `loadtest_<run_id>*`
- problems with the load-test title prefix or authored by load-test users
- submissions created by load-test users or linked to load-test problems
- pre-validation rows through submission cascade
- reports linked through `test_data.problem_id` / `test_data.submission_id`
- courses, contests, and sections created for the run
- uploaded submission files, polygon/problem data files, and load-user avatars

Run `summarize_load_test` again after cleanup; counts for that `run_id` should
be zero, except for file-delete failures reported by the cleanup command.

## 5. Recommended Profiles

Smoke:

```text
submissions: 20
polygon drafts: 20
duration: 60 seconds
file size: 1 MB
```

Medium:

```text
submissions: 1000
polygon drafts: 1000
duration: 10 minutes
file size: 50 MB
```

Stress:

```text
submissions: 5000+
polygon drafts: 5000+
duration: 30 minutes
file size: 50 MB+
```

Use only isolated staging data. These tests intentionally create many users,
submissions, files, reports, and problems.
