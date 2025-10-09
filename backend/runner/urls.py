from django.urls import path
from .views.authorization import register_view, login_view
from .views.submissions import submission_list, submission_detail, submission_compare

urlpatterns = [
    path('register/', register_view, name='register'),
    path('login/', login_view, name='login'),
    path('task/<int:task_id>/submissions/', submission_list, name="submission_list"),
    path('submission/<int:submission_id>/', submission_detail, name="submission_detail"),
    path('task/<int:task_id>/compare/', submission_compare, name="submission_compare"),
]
