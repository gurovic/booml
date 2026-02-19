from pathlib import Path
from django.http import JsonResponse
from django.core.paginator import Paginator, EmptyPage
from django.db.models import Q
from django.shortcuts import get_object_or_404
from rest_framework.decorators import api_view, parser_classes
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from rest_framework.response import Response
from rest_framework import status
from ..models.problem import Problem
from ..models.problem_desriptor import ProblemDescriptor
from ..models.problem_data import ProblemData
from ..services.metrics import get_available_metrics


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


@api_view(['GET'])
def get_polygon_problem_api(request, problem_id):
    """
    GET /backend/polygon/problems/<id>
    Returns detailed information about a problem including descriptor and data files
    """
    if not request.user.is_authenticated:
        return Response({'error': 'Authentication required'}, status=status.HTTP_401_UNAUTHORIZED)
    
    problem = get_object_or_404(Problem, pk=problem_id, author=request.user)
    descriptor = ProblemDescriptor.objects.filter(problem=problem).first()
    problem_data = ProblemData.objects.filter(problem=problem).first()
    
    # Serialize descriptor - return default values if not exists
    if descriptor:
        descriptor_data = {
            'id_column': descriptor.id_column,
            'target_column': descriptor.target_column,
            'id_type': descriptor.id_type,
            'target_type': descriptor.target_type,
            'check_order': descriptor.check_order,
            'metric_name': descriptor.metric_name,
            'metric_code': descriptor.metric_code,
        }
    else:
        # Return default descriptor values
        descriptor_data = {
            'id_column': 'id',
            'target_column': 'prediction',
            'id_type': 'int',
            'target_type': 'float',
            'check_order': False,
            'metric_name': 'rmse',
            'metric_code': '',
        }
    
    # Serialize problem data files
    files_data = {}
    if problem_data:
        for field_name in ('train_file', 'test_file', 'sample_submission_file', 'answer_file'):
            file_field = getattr(problem_data, field_name, None)
            if file_field:
                files_data[field_name] = {
                    'url': file_field.url,
                    'name': Path(file_field.name).name,
                    'size': file_field.size if hasattr(file_field, 'size') else None,
                }
    
    return Response({
        'id': problem.id,
        'title': problem.title,
        'rating': problem.rating,
        'statement': problem.statement,
        'is_published': problem.is_published,
        'created_at': problem.created_at.strftime('%Y-%m-%d') if problem.created_at else None,
        'author_username': problem.author.username if problem.author else None,
        'descriptor': descriptor_data,
        'files': files_data,
        'available_metrics': get_available_metrics(),
        'id_type_choices': [{'value': v, 'label': l} for v, l in ProblemDescriptor._meta.get_field('id_type').choices],
        'target_type_choices': [{'value': v, 'label': l} for v, l in ProblemDescriptor._meta.get_field('target_type').choices],
    }, status=status.HTTP_200_OK)


@api_view(['PUT', 'PATCH'])
def update_polygon_problem_api(request, problem_id):
    """
    PUT/PATCH /backend/polygon/problems/<id>
    Updates problem information
    """
    if not request.user.is_authenticated:
        return Response({'error': 'Authentication required'}, status=status.HTTP_401_UNAUTHORIZED)
    
    problem = get_object_or_404(Problem, pk=problem_id, author=request.user)
    
    errors = {}
    
    # Update basic problem fields
    if 'title' in request.data:
        title = (request.data.get('title') or '').strip()
        if not title:
            errors['title'] = 'Название обязательно'
        else:
            problem.title = title
    
    if 'rating' in request.data:
        try:
            rating = int(request.data.get('rating'))
            rating_field = Problem._meta.get_field('rating')
            min_rating = max_rating = None
            for v in getattr(rating_field, 'validators', []):
                limit = getattr(v, 'limit_value', None)
                name = v.__class__.__name__.lower()
                if 'min' in name:
                    min_rating = limit
                if 'max' in name:
                    max_rating = limit
            if min_rating is not None and max_rating is not None:
                if not (min_rating <= rating <= max_rating):
                    errors['rating'] = f'Рейтинг должен быть от {min_rating} до {max_rating}'
            if not errors.get('rating'):
                problem.rating = rating
        except (TypeError, ValueError):
            errors['rating'] = 'Рейтинг должен быть целым числом'
    
    if 'statement' in request.data:
        problem.statement = request.data.get('statement') or ''
    
    if not errors:
        problem.save()
    
    # Update descriptor if provided
    if 'descriptor' in request.data and not errors:
        descriptor_data = request.data.get('descriptor', {})
        descriptor_errors = {}
        
        descriptor_fields = {
            'id_column': (descriptor_data.get('id_column') or '').strip(),
            'target_column': (descriptor_data.get('target_column') or '').strip(),
            'id_type': (descriptor_data.get('id_type') or '').strip(),
            'target_type': (descriptor_data.get('target_type') or '').strip(),
            'check_order': descriptor_data.get('check_order', False),
            'metric_name': (descriptor_data.get('metric_name') or '').strip(),
            'metric_code': descriptor_data.get('metric_code') or '',
        }
        
        if not descriptor_fields['id_column']:
            descriptor_errors['id_column'] = 'Колонка идентификатора обязательна'
        if not descriptor_fields['target_column']:
            descriptor_errors['target_column'] = 'Колонка ответа обязательна'
        
        id_type_choices = {choice for choice, _ in ProblemDescriptor._meta.get_field('id_type').choices}
        target_type_choices = {choice for choice, _ in ProblemDescriptor._meta.get_field('target_type').choices}
        
        if descriptor_fields['id_type'] not in id_type_choices:
            descriptor_errors['id_type'] = 'Неверный тип идентификатора'
        if descriptor_fields['target_type'] not in target_type_choices:
            descriptor_errors['target_type'] = 'Неверный тип ответа'
        
        if not descriptor_fields['metric_name']:
            descriptor_errors['metric_name'] = 'Укажите метрику'
        elif not descriptor_fields['metric_code'] and descriptor_fields['metric_name'] not in set(get_available_metrics()):
            descriptor_errors['metric_name'] = 'Выберите метрику из списка или добавьте Python код'
        
        if descriptor_errors:
            errors['descriptor'] = descriptor_errors
        else:
            ProblemDescriptor.objects.update_or_create(
                problem=problem,
                defaults=descriptor_fields
            )
    
    if errors:
        return Response({'errors': errors}, status=status.HTTP_400_BAD_REQUEST)
    
    # Return updated problem
    descriptor = ProblemDescriptor.objects.filter(problem=problem).first()
    descriptor_data = None
    if descriptor:
        descriptor_data = {
            'id_column': descriptor.id_column,
            'target_column': descriptor.target_column,
            'id_type': descriptor.id_type,
            'target_type': descriptor.target_type,
            'check_order': descriptor.check_order,
            'metric_name': descriptor.metric_name,
            'metric_code': descriptor.metric_code,
        }
    
    return Response({
        'id': problem.id,
        'title': problem.title,
        'rating': problem.rating,
        'statement': problem.statement,
        'is_published': problem.is_published,
        'created_at': problem.created_at.strftime('%Y-%m-%d') if problem.created_at else None,
        'descriptor': descriptor_data,
    }, status=status.HTTP_200_OK)


@api_view(['POST'])
@parser_classes([MultiPartParser, FormParser])
def upload_polygon_problem_file_api(request, problem_id):
    """
    POST /backend/polygon/problems/<id>/upload
    Uploads data files for a problem
    """
    if not request.user.is_authenticated:
        return Response({'error': 'Authentication required'}, status=status.HTTP_401_UNAUTHORIZED)
    
    problem = get_object_or_404(Problem, pk=problem_id, author=request.user)
    
    ALLOWED_EXTENSIONS = {
        'train_file': ('.csv', '.zip', '.rar'),
        'test_file': ('.csv', '.zip', '.rar'),
        'sample_submission_file': ('.csv',),
        'answer_file': ('.csv',),
    }
    
    errors = {}
    uploaded_files = {}
    
    for field_name in ALLOWED_EXTENSIONS.keys():
        file_obj = request.FILES.get(field_name)
        if file_obj:
            filename = getattr(file_obj, 'name', '') or ''
            ext = Path(filename).suffix.lower()
            allowed = ALLOWED_EXTENSIONS[field_name]
            
            if ext not in allowed:
                allowed_label = '/'.join(e.lstrip('.').upper() for e in allowed)
                errors[field_name] = f'Файл должен быть в формате {allowed_label}'
            else:
                uploaded_files[field_name] = file_obj
    
    if errors:
        return Response({'errors': errors}, status=status.HTTP_400_BAD_REQUEST)
    
    if uploaded_files:
        problem_data, _ = ProblemData.objects.get_or_create(problem=problem)
        for field_name, file_obj in uploaded_files.items():
            setattr(problem_data, field_name, file_obj)
        problem_data.save()
    
    # Return updated files info
    problem_data = ProblemData.objects.filter(problem=problem).first()
    files_data = {}
    if problem_data:
        for field_name in ALLOWED_EXTENSIONS.keys():
            file_field = getattr(problem_data, field_name, None)
            if file_field:
                files_data[field_name] = {
                    'url': file_field.url,
                    'name': Path(file_field.name).name,
                    'size': file_field.size if hasattr(file_field, 'size') else None,
                }
    
    return Response({
        'files': files_data,
        'message': 'Файлы успешно загружены'
    }, status=status.HTTP_200_OK)


@api_view(['POST'])
def publish_polygon_problem_api(request, problem_id):
    """
    POST /backend/polygon/problems/<id>/publish
    Publishes a problem after validation
    """
    if not request.user.is_authenticated:
        return Response({'error': 'Authentication required'}, status=status.HTTP_401_UNAUTHORIZED)
    
    problem = get_object_or_404(Problem, pk=problem_id, author=request.user)
    
    if problem.is_published:
        return Response({'message': 'Задача уже опубликована'}, status=status.HTTP_200_OK)
    
    errors = []
    
    if not (problem.title or '').strip():
        errors.append('Заполните название задачи')
    
    if problem.rating is None:
        errors.append('Заполните рейтинг задачи')
    
    if not (problem.statement or '').strip():
        errors.append('Заполните условие задачи')
    
    descriptor = ProblemDescriptor.objects.filter(problem=problem).first()
    if not descriptor:
        errors.append('Заполните описание данных (descriptor)')
    else:
        for field_name in ('id_column', 'target_column', 'id_type', 'target_type'):
            value = getattr(descriptor, field_name, '')
            if not value:
                errors.append('Заполните все поля описания данных')
                break
        metric_name = (getattr(descriptor, 'metric_name', '') or '').strip()
        metric_code = (getattr(descriptor, 'metric_code', '') or '').strip()
        if not metric_name:
            errors.append('Укажите метрику качества для задачи')
        elif not metric_code and metric_name not in set(get_available_metrics()):
            errors.append('Выберите стандартную метрику или добавьте Python код для своей метрики')
    
    data = ProblemData.objects.filter(problem=problem).first()
    if not data or not data.answer_file:
        errors.append('Добавьте файл ответов answer.csv')
    elif not data.answer_file.name.lower().endswith('.csv'):
        errors.append('Файл ответов должен быть в формате CSV')
    
    if errors:
        return Response({'errors': errors}, status=status.HTTP_400_BAD_REQUEST)
    
    problem.is_published = True
    problem.save(update_fields=['is_published'])
    
    return Response({
        'message': 'Задача успешно опубликована',
        'is_published': True
    }, status=status.HTTP_200_OK)
