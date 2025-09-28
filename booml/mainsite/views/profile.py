from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth import get_user_model
from mainsite.models.solution import Solution

User = get_user_model()

def profile_view(request, username):
    user_profile = get_object_or_404(User, username=username)
    # список последних N решений (на странице профиля показываем превью)
    recent_solutions = Solution.objects.filter(user=user_profile).select_related('problem')[:10]

    # Показываем email только владельцу профиля (конфиденциально) — опция:
    show_email = request.user.is_authenticated and (request.user == user_profile or request.user.is_staff)

    return render(request, 'users/profile.html', {
        'user_profile': user_profile,
        'recent_solutions': recent_solutions,
        'show_email': show_email,
    })

def solved_list_view(request, username):
    user_profile = get_object_or_404(User, username=username)
    solved = Solution.objects.filter(user=user_profile).select_related('problem')
    return render(request, 'users/solved_list.html', {
        'user_profile': user_profile,
        'solved': solved,
    })
