from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from ..models.problem import Problem


@require_http_methods(["GET"])
def polygon_problems_api(request):
    """
    GET /backend/polygon/problems
    Returns list of problems created by the current user
    """
    if not request.user.is_authenticated:
        return JsonResponse({'error': 'Authentication required'}, status=401)
    
    problems = Problem.objects.filter(author=request.user).order_by('-id')
    
    data = []
    for problem in problems:
        data.append({
            'id': problem.id,
            'title': problem.title,
            'rating': problem.rating,
            'is_published': problem.is_published,
            'created_at': problem.created_at.strftime('%Y-%m-%d') if problem.created_at else None
        })
    
    return JsonResponse(data, safe=False)


@require_http_methods(["POST"])
def create_polygon_problem_api(request):
    """
    POST /backend/polygon/problems/create
    Creates a new problem
    """
    if not request.user.is_authenticated:
        return JsonResponse({'error': 'Authentication required'}, status=401)
    
    import json
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)
    
    title = (data.get('title') or '').strip()
    if not title:
        return JsonResponse({'error': 'Title is required'}, status=400)
    
    rating = data.get('rating', 800)
    try:
        rating = int(rating)
    except (TypeError, ValueError):
        return JsonResponse({'error': 'Rating must be a number'}, status=400)
    
    problem = Problem.objects.create(
        title=title,
        rating=rating,
        author=request.user,
        is_published=False
    )
    
    return JsonResponse({
        'id': problem.id,
        'title': problem.title,
        'rating': problem.rating,
        'is_published': problem.is_published,
        'created_at': problem.created_at.strftime('%Y-%m-%d') if problem.created_at else None
    }, status=201)
