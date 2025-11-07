import pytest
from django.urls import reverse
from runner.models import NotebookCell


@pytest.mark.django_db
def test_duplicate_cell(client, notebook):
    cell = NotebookCell.objects.create(notebook=notebook, content="print(1)")
    url = reverse("runner:duplicate_cell", args=[notebook.id, cell.id])
    response = client.post(url)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert NotebookCell.objects.count() == 2


@pytest.mark.django_db
def test_reorder_cells(client, notebook):
    cells = [
        NotebookCell.objects.create(notebook=notebook, execution_order=i)
        for i in range(3)
    ]
    url = reverse("runner:reorder_cells", args=[notebook.id])
    new_order = [cells[2].id, cells[0].id, cells[1].id]
    response = client.post(url, content_type="application/json", data={"order": new_order})
    assert response.status_code == 200
