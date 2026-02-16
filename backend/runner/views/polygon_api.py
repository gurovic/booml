from django.http import JsonResponse
from django.core.paginator import Paginator, EmptyPage
from django.db.models import Q
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
from ..models.problem import Problem


@api_view(['GET'])
def polygon_problems_api(request):
    """
    GET /backend/polygon/problems
    Returns list of problems visible to the current user.

    Visibility rules:
    - Own problems (drafts + published) are always visible.
    - Other users' problems are visible only if they are published.
    - Staff/superuser can see all problems.
    """
    if not request.user.is_authenticated:
        return Response({'error': 'Authentication required'}, status=status.HTTP_401_UNAUTHORIZED)
    
    q = (request.GET.get("q") or "").strip()
    page_raw = request.GET.get("page")
    page_size_raw = request.GET.get("page_size")
    use_paging = bool(q) or page_raw is not None or page_size_raw is not None

    problems_qs = Problem.objects.all()
    if not (request.user.is_staff or request.user.is_superuser):
        # Keep drafts private: only the author can see them.
        problems_qs = problems_qs.filter(Q(author=request.user) | Q(is_published=True))
    if q:
        problems_qs = problems_qs.filter(title__icontains=q)
    problems_qs = problems_qs.order_by("-id")
    
    def serialize(problem):
        return {
            "id": problem.id,
            "title": problem.title,
            "rating": problem.rating,
            "is_published": problem.is_published,
            "author_username": getattr(problem.author, "username", None),
            "created_at": problem.created_at.strftime("%Y-%m-%d") if problem.created_at else None,
        }

    if not use_paging:
        return Response([serialize(p) for p in problems_qs], status=status.HTTP_200_OK)

    try:
        page_size = int(page_size_raw or 20)
    except (TypeError, ValueError):
        page_size = 20
    page_size = max(1, min(page_size, 100))

    try:
        page = int(page_raw or 1)
    except (TypeError, ValueError):
        page = 1
    page = max(1, page)

    paginator = Paginator(problems_qs, page_size)
    try:
        page_obj = paginator.page(page)
    except EmptyPage:
        page_obj = paginator.page(paginator.num_pages) if paginator.num_pages else []

    items = [serialize(p) for p in (page_obj.object_list if page_obj else [])]
    return Response(
        {
            "items": items,
            "q": q,
            "page": page_obj.number if page_obj else 1,
            "page_size": page_size,
            "total": paginator.count,
            "total_pages": paginator.num_pages,
        },
        status=status.HTTP_200_OK,
    )


@api_view(['POST'])
def create_polygon_problem_api(request):
    """
    POST /backend/polygon/problems/create
    Creates a new problem
    """
    if not request.user.is_authenticated:
        return Response({'error': 'Authentication required'}, status=status.HTTP_401_UNAUTHORIZED)
    
    title = (request.data.get('title') or '').strip()
    if not title:
        return Response({'error': 'Title is required'}, status=status.HTTP_400_BAD_REQUEST)
    
    rating = request.data.get('rating', 800)
    try:
        rating = int(rating)
    except (TypeError, ValueError):
        return Response({'error': 'Rating must be a number'}, status=status.HTTP_400_BAD_REQUEST)
    
    problem = Problem.objects.create(
        title=title,
        rating=rating,
        author=request.user,
        is_published=False
    )
    
    return Response({
        'id': problem.id,
        'title': problem.title,
        'rating': problem.rating,
        'is_published': problem.is_published,
        'created_at': problem.created_at.strftime('%Y-%m-%d') if problem.created_at else None
    }, status=status.HTTP_201_CREATED)
