from django.http import JsonResponse
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
from ..models.problem import Problem


@api_view(['GET'])
def polygon_problems_api(request):
    """
    GET /backend/polygon/problems
    Returns list of problems created by the current user
    """
    if not request.user.is_authenticated:
        return Response({'error': 'Authentication required'}, status=status.HTTP_401_UNAUTHORIZED)
    
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
    
    return Response(data, status=status.HTTP_200_OK)


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
