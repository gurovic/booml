from .main_page import main_page
from .authorization import register_view, login_view
from .contest_draft import (
    create_contest,
    contest_success,
    contest_detail,
    course_detail,
    list_contests,
    set_contest_access,
    manage_contest_participants,
)
from .problems import problem_list
from .get_reports_list import get_reports_list
from .receive_test_result import receive_test_result
from .submissions import extract_labels_and_metrics, submission_list, submission_detail, submission_compare
from .problem_detail import problem_detail
from .run_code import run_code
from .delete_cell import delete_cell
from .create_cell import create_cell
from .save_cell_output import save_cell_output
from .notebook_detail import notebook_detail
from .create_notebook import create_notebook
from .notebook_list import notebook_list
from .get_reports_list import get_reports_list
from .receive_test_result import receive_test_result
from .problem_detail import problem_detail
from .contest_draft import create_contest
from .contest_draft import contest_success
