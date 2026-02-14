# Notebook-Based Contests

This document describes the notebook-based contest feature that allows teachers to create contests where students work in Jupyter-style notebooks and submit their entire notebook for evaluation.

## Overview

Notebook-based contests provide an alternative to traditional problem-based contests. Instead of submitting CSV files for individual problems, students:

1. Work on a notebook with task cells
2. Write and run code in solution cells after each task
3. Submit the entire notebook for evaluation
4. Receive automated feedback based on cell outputs

## Architecture

### Database Models

#### Contest Model Updates
- **contest_type**: Field to distinguish between "regular" and "notebook" contests (default: "regular")
- **template_notebook**: Optional FK to a Notebook that serves as the contest template

#### Cell Model Updates
- **is_task_cell**: Boolean flag to mark cells as task cells
- **problem**: Optional FK to Problem for task cells

#### NotebookSubmission Model (New)
- Tracks notebook submissions for notebook-based contests
- Stores per-cell metrics and overall score
- Fields:
  - `user`: FK to User
  - `contest`: FK to Contest
  - `notebook`: FK to Notebook
  - `status`: Submission status (pending, running, accepted, failed, etc.)
  - `metrics`: JSONField storing results for each task cell
  - `total_score`: Float representing average score across all task cells

### Services

#### NotebookSubmissionChecker
Located in `backend/runner/services/notebook_checker.py`

**Key Methods:**
- `check_notebook_submission(notebook_submission)`: Main entry point for checking a notebook submission
- `_check_task_cell(task_cell)`: Validates a single task cell's output against expected results

**Checking Logic:**
1. Extracts output from each task cell in the notebook
2. Parses output as CSV
3. Compares against the problem's expected answer file using CSV matching
4. Calculates average score across all task cells
5. Marks submission as ACCEPTED only if all tasks have perfect scores (1.0)

The checker reuses the existing CSV matching logic from `SubmissionChecker._calculate_csv_match()`.

### API Endpoints

#### Create Notebook Submission
```
POST /api/notebook-submissions/
Content-Type: application/json

{
  "contest_id": <int>,
  "notebook_id": <int>
}
```

**Response (201 Created):**
```json
{
  "id": 123,
  "user": 1,
  "username": "student1",
  "contest_id": 5,
  "contest_title": "Notebook Contest 1",
  "notebook_id": 42,
  "notebook_title": "My Solution",
  "submitted_at": "2026-02-14T19:30:00Z",
  "status": "accepted",
  "metrics": {
    "101": {"score": 1.0, "metric": "csv_match"},
    "102": {"score": 1.0, "metric": "csv_match"}
  },
  "total_score": 1.0
}
```

**Validation:**
- Contest must exist and be of type "notebook"
- Notebook must exist and belong to the authenticated user
- Notebook must have at least one task cell

#### List User's Submissions
```
GET /api/notebook-submissions/mine/
```

Returns paginated list of user's notebook submissions, ordered by submission time (newest first).

#### Get Submission Detail
```
GET /api/notebook-submissions/<id>/
```

Returns detailed information about a specific submission. Users can only access their own submissions.

## Usage Example

### 1. Teacher Creates Notebook Contest

```python
# Create contest
contest = Contest.objects.create(
    title="ML Contest Week 1",
    course=course,
    contest_type=Contest.ContestType.NOTEBOOK,
    created_by=teacher
)

# Create template notebook with task cells
template = Notebook.objects.create(
    title="Contest Template",
    owner=teacher
)

# Add task description cell
Cell.objects.create(
    notebook=template,
    cell_type=Cell.TEXT,
    content="## Task 1: Predict values\n\nYour code should output CSV with columns: id, value",
    execution_order=1
)

# Add task cell linked to problem
Cell.objects.create(
    notebook=template,
    cell_type=Cell.CODE,
    content="# Your solution here\n",
    is_task_cell=True,
    problem=problem1,
    execution_order=2
)

contest.template_notebook = template
contest.save()
```

### 2. Student Works on Notebook

Students copy the template or create their own notebook, write code in cells, and run them to produce outputs.

```python
# Student's solution cell
solution_cell = Cell.objects.create(
    notebook=student_notebook,
    cell_type=Cell.CODE,
    content="import pandas as pd\ndf = pd.DataFrame({'id': [1,2,3], 'value': [10,20,30]})\nprint(df.to_csv(index=False))",
    output="id,value\n1,10\n2,20\n3,30\n",  # Output captured after execution
    is_task_cell=True,
    problem=problem1,
    execution_order=2
)
```

### 3. Student Submits Notebook

```python
# Via API
POST /api/notebook-submissions/
{
  "contest_id": contest.id,
  "notebook_id": student_notebook.id
}

# Or programmatically
submission = NotebookSubmission.objects.create(
    user=student,
    contest=contest,
    notebook=student_notebook
)

checker = NotebookSubmissionChecker()
result = checker.check_notebook_submission(submission)
```

### 4. System Evaluates Submission

The checker:
1. Finds all task cells in the notebook
2. For each task cell:
   - Parses the cell's output as CSV
   - Loads the problem's answer file
   - Compares using CSV matching (exact match with tolerance for floats)
   - Records score (1.0 for match, 0.0 for mismatch)
3. Calculates average score
4. Updates submission status:
   - ACCEPTED if all tasks have perfect scores
   - FAILED otherwise

## CSV Matching

The notebook checker uses the same CSV matching logic as regular submissions:

- **Column validation**: Submission must have exactly the columns in the answer file
- **Row count validation**: Must have the same number of rows
- **ID validation**: If an ID column is specified, IDs must match
- **Value comparison**: Uses pandas `assert_frame_equal` with tolerances:
  - `rtol=1e-6` (relative tolerance)
  - `atol=1e-8` (absolute tolerance)
- **Order**: Can be ignored if `check_order=False` in problem descriptor

## Testing

Comprehensive tests are provided:

### Model Tests
`backend/runner/models/test_notebook_submission.py`
- Creating submissions
- Storing metrics and scores
- Ordering by submission time

### Service Tests
`backend/runner/services/test_notebook_checker.py`
- Checking single task cells (correct/incorrect outputs)
- Checking multiple task cells
- Handling cells without output
- Validation errors (wrong contest type, no task cells)

### API Tests
`backend/runner/api/views/test_notebook_submissions.py`
- Creating submissions with validation
- Listing user submissions
- Getting submission details
- Permission checks

## Future Enhancements

Potential improvements:
1. **Async checking**: Use Celery for notebook checking instead of synchronous execution
2. **Partial credit**: Allow configurable scoring thresholds instead of requiring perfect scores
3. **Custom metrics**: Support metrics beyond CSV matching (e.g., RMSE, accuracy)
4. **Template copying**: Automatic notebook copying from contest template for students
5. **Progress tracking**: Track which task cells have been completed
6. **Time limits**: Add execution time limits per cell
7. **Resource limits**: Memory and CPU constraints per notebook

## Migration

Database migration `0024_notebook_contests.py` adds all necessary fields and tables. Run:

```bash
python manage.py migrate runner
```

## API Documentation

All endpoints require authentication. Responses follow the standard REST pattern with appropriate HTTP status codes:

- `200 OK`: Successful GET request
- `201 Created`: Successful POST request
- `400 Bad Request`: Validation error
- `403 Forbidden`: Not authenticated
- `404 Not Found`: Resource not found or not accessible

Error responses include descriptive messages:

```json
{
  "contest_id": ["Contest is not a notebook-based contest"],
  "notebook_id": ["You can only submit your own notebooks"]
}
```
