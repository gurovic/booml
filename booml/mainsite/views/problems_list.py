from mainsite.models import Problem


def get_all_problems():
    """
    Возвращает контекст со списком задач для включения в другие страницы
    """

    problems = Problem.objects.all()
    return {'problems': problems}
