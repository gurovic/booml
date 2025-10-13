from django.urls import path
from .views import (
    notebook_list,
    create_notebook,
    notebook_detail,
    create_cell,
    delete_cell,
    save_cell_output,
    execute_cell,
)


app_name = 'notebook'

urlpatterns = [
    path('', notebook_list, name='notebook_list'),
    path('new/', create_notebook, name='create_notebook'),
    path('<int:notebook_id>/', notebook_detail, name='notebook_detail'),
    path('<int:notebook_id>/cell/new/', create_cell, name='create_cell'),
    path('<int:notebook_id>/cell/<int:cell_id>/delete/', delete_cell, name='delete_cell'),
    path('<int:notebook_id>/cell/<int:cell_id>/execute/', execute_cell, name='execute_cell'),
    path('<int:notebook_id>/cell/<int:cell_id>/save_output/', save_cell_output, name='save_cell_output'),
]