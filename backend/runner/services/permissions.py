from django.core.exceptions import PermissionDenied
from django.http import Http404

from ..models import Notebook
from ..models.profile import Profile


def get_user_notebook_or_404(user, notebook_id):
    try:
        nb = Notebook.objects.get(id=notebook_id)
    except Notebook.DoesNotExist:
        raise Http404("Notebook not found")

    if nb.owner is None:
        return nb

    if not getattr(user, "is_authenticated", False):
        raise Http404("Notebook not found")

    if nb.owner != user:
        raise Http404("Notebook not found")

    return nb


def get_user_writable_notebook_or_404(user, notebook_id):
    try:
        notebook = Notebook.objects.get(id=notebook_id)
    except Notebook.DoesNotExist:
        raise Http404("Notebook not found")

    if not getattr(user, "is_authenticated", False):
        return notebook
    if notebook.owner is not None and notebook.owner != user:
        raise PermissionDenied("Недостаточно прав для работы с этим блокнотом")
    return notebook


def user_has_gpu_access(user) -> bool:
    if user is None or not getattr(user, "is_authenticated", False):
        return False
    profile = getattr(user, "profile", None)
    if profile is None:
        profile, _ = Profile.objects.get_or_create(user=user)
    return bool(getattr(profile, "gpu_access", False))
