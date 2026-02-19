def is_platform_admin(user) -> bool:
    """
    Global catalog admin for sections/courses.

    Rules:
    - any Django superuser
    - dedicated staff account with username "admin"
    """

    if user is None or not getattr(user, "is_authenticated", False):
        return False
    if bool(getattr(user, "is_superuser", False)):
        return True
    return (
        bool(getattr(user, "is_staff", False))
        and str(getattr(user, "username", "")).strip().lower() == "admin"
    )
