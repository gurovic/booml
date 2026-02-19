def is_platform_admin(user) -> bool:
    """
    Global catalog admin for sections/courses.

    Rules:
    - any Django superuser
    - dedicated account with username "admin"
    """

    if user is None or not getattr(user, "is_authenticated", False):
        return False
    if bool(getattr(user, "is_superuser", False)):
        return True
    return str(getattr(user, "username", "")).strip().lower() == "admin"
