from .main_page import main_page
from .authorization import register_view, login_view
from .contest_draft import create_contest, contest_success
from .tasks import task_list
from .get_reports_list import get_reports_list
from .receive_test_result import receive_test_result
from .submissions import extract_labels_and_metrics, submission_list, submission_detail, submission_compare
from .task_detail import task_detail
