from rest_framework import permissions


class IsTeacher(permissions.BasePermission):
    """
    Permission that allows access only to users with the teacher role.
    Teachers are identified by is_staff=True (set during registration).
    """

    message = "Only teachers can perform this action."

    def has_permission(self, request, view):
        return (
            request.user
            and request.user.is_authenticated
            and request.user.is_staff
        )
