from django.urls import path
from .views.submissions import submission_list, submission_detail, submission_compare, recent_submissions
from .views.main_page import main_page
from .views.problem_detail import problem_detail, problem_detail_api, problem_file_download_api
from .views.authorization import register_view, login_view, logout_view, backend_register, backend_login, \
    backend_logout, backend_current_user, backend_check_auth, get_csrf_token
from .views.problems import problem_list
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

from .views.notebook_list import notebook_list
from .views.create_notebook import create_notebook
from .views.delete_notebook import delete_notebook
from .views.rename_notebook import rename_notebook
from .views.notebook_detail import notebook_detail, notebook_detail_api
from .views.update_notebook_device import update_notebook_device
from .views.create_cell import create_cell, create_latex_cell
from .views.delete_cell import delete_cell
from .views.save_cell_output import save_cell_output
from .views.save_text_cell import save_text_cell
from .views.create_text_cell import create_text_cell
from .views.import_notebook import import_notebook
from .views.export_notebook import export_notebook
from .views.reorder_cells import copy_cell, move_cell
from .views.get_reports_list import get_reports_list
from .views.receive_test_result import receive_test_result
from .views.contest_draft import (
    add_problem_to_contest,
    bulk_add_problems_to_contest,
    contest_detail,
    create_contest,
    contest_success,
    delete_contest,
    list_contests,
    manage_contest_participants,
    list_pending_contests,
    moderate_contest,
    reorder_contest_problems,
    remove_problem_from_contest,
    set_contest_access,
)
from .views.contest_leaderboard import contest_problem_leaderboard
from .views.course import course_contests, course_detail
from .views.course import (
    update_course,
    delete_course,
    update_course_participants,
    remove_course_participants,
    reorder_course_contests,
)
from .views.run_code import run_code
from .views.list_of_problems_polygon import problem_list_polygon
from .views.create_problem_polygon import create_problem_polygon
from .views.edit_problem_polygon import edit_problem_polygon
from .views.publish_problem_polygon import publish_problem_polygon
from .views.polygon_api import polygon_problems_api, create_polygon_problem_api
from .views.api import start_api
from .views.profile import (get_my_profile,
                            get_profile_by_id,
                            update_avatar,
                            delete_avatar,
                            update_profile_info,
                            )


app_name = 'runner'


urlpatterns = [
    # GET /runner/api/reports/ - получить список всех отчётов
    path('api/reports/', get_reports_list, name='reports-list'),
    # POST /runner/api/reports/create/ - создать новый отчёт
    path('api/reports/create/', receive_test_result, name='receive-test-result'),
    path("", main_page, name="main_page"),
    path('register/', register_view, name='register'),
    path('login/', login_view, name='login'),
    path('problem/<int:problem_id>/submissions/', submission_list, name="submission_list"),
    path('logout/', logout_view, name='logout'),
    path('submission/<int:submission_id>/', submission_detail, name="submission_detail"),
    path('submissions/recent', recent_submissions, name='recent_submissions'),
    path('problem/<int:problem_id>/compare/', submission_compare, name="submission_compare"),
    path("problems/<int:problem_id>/", problem_detail, name="problem_detail"),
    path("problems/", problem_list, name="problem_list"),
    path('course/<int:course_id>/', course_detail, name='course_detail'),
    path('course/<int:course_id>/contests/', course_contests, name='course_contests'),
    path('backend/course/<int:course_id>/update/', update_course, name='backend_course_update'),
    path('backend/course/<int:course_id>/delete/', delete_course, name='backend_course_delete'),
    path('backend/course/<int:course_id>/participants/update/', update_course_participants, name='backend_course_participants_update'),
    path('backend/course/<int:course_id>/participants/remove/', remove_course_participants, name='backend_course_participants_remove'),
    path('backend/course/<int:course_id>/contests/reorder/', reorder_course_contests, name='backend_course_contests_reorder'),
    path('contest/', list_contests, name='contest_list'),
    path('contest/<int:contest_id>/', contest_detail, name='contest_detail'),
    path('contest/<int:contest_id>/leaderboard/', contest_problem_leaderboard, name='contest_problem_leaderboard'),
    path('contest/<int:course_id>/new/', create_contest, name='create_contest'),
    path('contest/<int:contest_id>/delete/', delete_contest, name='delete_contest'),
    path('contest/<int:contest_id>/access/', set_contest_access, name='contest_set_access'),
    path('contest/<int:contest_id>/participants/', manage_contest_participants, name='contest_manage_participants'),
    path('contest/<int:contest_id>/problems/add/', add_problem_to_contest, name='contest_add_problem'),
    path('contest/<int:contest_id>/problems/bulk_add/', bulk_add_problems_to_contest, name='contest_bulk_add_problems'),
    path('contest/<int:contest_id>/problems/reorder/', reorder_contest_problems, name='contest_reorder_problems'),
    path('contest/<int:contest_id>/problems/remove/', remove_problem_from_contest, name='contest_remove_problem'),
    path('contest/<int:contest_id>/moderate/', moderate_contest, name='contest_moderate'),
    path('contests/pending/', list_pending_contests, name='contest_list_pending'),
    path('contest/success/', contest_success, name='contest_success'),
    path('notebook', notebook_list, name='notebook_list'),
    path('notebook/new/', create_notebook, name='create_notebook'),
    path('notebook/<int:notebook_id>/delete/', delete_notebook, name='delete_notebook'),
    path('notebook/<int:notebook_id>/rename/', rename_notebook, name='rename_notebook'),
    path('notebook/<int:notebook_id>/device/', update_notebook_device, name='update_notebook_device'),
    path('notebook/<int:notebook_id>/', notebook_detail, name='notebook_detail'),
    path('backend/notebook/<int:notebook_id>/', notebook_detail_api, name='backend_notebook_detail'),
    path('backend/notebook/<int:notebook_id>/cell/<int:cell_id>/save_output/', save_cell_output, name='backend_save_cell_output'),
    path('backend/notebook/<int:notebook_id>/cell/<int:cell_id>/save_text/', save_text_cell, name='backend_save_text_cell'),
    path('notebook/<int:notebook_id>/cell/new/', create_cell, name='create_cell'),
    path('notebook/<int:notebook_id>/cell/new/latex/', create_latex_cell, name='create_latex_cell'),
    path('notebook/<int:notebook_id>/cell/<int:cell_id>/delete/', delete_cell, name='delete_cell'),
    path('notebook/<int:notebook_id>/cell/<int:cell_id>/copy/', copy_cell, name='copy_cell'),
    path('notebook/<int:notebook_id>/cell/<int:cell_id>/move/', move_cell, name='move_cell'),
    path('notebook/<int:notebook_id>/cell/<int:cell_id>/save_output/', save_cell_output, name='save_cell_output'),
    path('notebook/<int:notebook_id>/cell/<int:cell_id>/save_text/', save_text_cell, name='save_text_cell'),
    path('notebook/<int:notebook_id>/create_text_cell/', create_text_cell, name='create_text_cell'),
    path('notebook/import/', import_notebook, name='import_notebook'),
    path('notebook/<int:notebook_id>/export/', export_notebook, name='export_notebook'),
    path('run_code/', run_code, name='run_code'),
    path('polygon/', problem_list_polygon, name='polygon'),
    path('polygon/new/', create_problem_polygon, name='polygon_create_problem'),
    path('polygon/problem/<int:problem_id>/', edit_problem_polygon, name='polygon_edit_problem'),
    path('polygon/problem/<int:problem_id>/publish/', publish_problem_polygon, name='polygon_publish_problem'),

    path('backend/problem/', problem_detail_api, name='backend_problem_detail'),
    path('backend/problem/<int:problem_id>/file/', problem_file_download_api, name='backend_problem_file_download'),
    path('backend/start/', start_api),
    path('backend/polygon/problems', polygon_problems_api),
    path('backend/polygon/problems/create', create_polygon_problem_api),
    path('backend/course/<int:course_id>/', course_detail, name='backend_course_detail'),
    path('backend/contest/', list_contests, name='backend_contest_list'),
    path('backend/contest/<int:contest_id>/', contest_detail, name='backend_contest_detail'),
    # Frontend talks to backend through /backend/* (see frontend devServer proxy).
    path('backend/contest/<int:course_id>/new/', create_contest, name='backend_create_contest'),
    path('backend/contest/<int:contest_id>/delete/', delete_contest, name='backend_delete_contest'),
    path(
        'backend/contest/<int:contest_id>/leaderboard/',
        contest_problem_leaderboard,
        name='backend_contest_leaderboard',
    ),
    path(
        'backend/contest/<int:contest_id>/problems/add/',
        add_problem_to_contest,
        name='backend_contest_add_problem',
    ),
    path(
        'backend/contest/<int:contest_id>/problems/bulk_add/',
        bulk_add_problems_to_contest,
        name='backend_contest_bulk_add_problem',
    ),
    path(
        'backend/contest/<int:contest_id>/problems/reorder/',
        reorder_contest_problems,
        name='backend_contest_reorder_problems',
    ),
    path(
        'backend/contest/<int:contest_id>/problems/remove/',
        remove_problem_from_contest,
        name='backend_contest_remove_problem',
    ),
    path('backend/register/', backend_register, name='backend_register'),
    path('backend/login/', backend_login, name='backend_login'),
    path('backend/logout/', backend_logout, name='backend_logout'),
    path('backend/user/', backend_current_user, name='backend_current_user'),
    path('backend/check-auth/', backend_check_auth, name='backend_check_auth'),
    path('backend/csrf-token/', get_csrf_token, name='backend_csrf_token'),
    path('backend/token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('backend/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('backend/profiles/me/', get_my_profile, name='profile-me'),
    path('backend/profiles/<int:user_id>/', get_profile_by_id, name='profile-detail'),
    path('backend/profiles/update-avatar/', update_avatar, name='profile-update-avatar'),
    path('backend/profiles/delete-avatar/', delete_avatar, name='profile-delete-avatar'),
    path('backend/profiles/update-info/', update_profile_info, name='profile-update-info'),
]
