# Copilot Instructions for booml

## Project Overview

This is **booml**, a machine learning platform with a Django backend and Vue.js frontend. The platform allows students to work on ML tasks, submit code for execution in isolated environments, and track their progress through courses and contests.

## Architecture

### Backend (Django)
- **Location**: `/backend`
- **Framework**: Django 5.2.8 with Django REST Framework
- **Python Version**: 3.14
- **Database**: PostgreSQL 16
- **Task Queue**: Celery with Redis
- **Real-time**: Django Channels with Redis
- **Code Execution**: Jupyter kernel-based runtime with Docker VM isolation

### Frontend (Vue.js)
- **Location**: `/frontend`
- **Framework**: Vue 3 with Vue Router and Pinia
- **Build Tool**: Vue CLI 5
- **Linting**: ESLint with Vue 3 recommended config

## Project Structure

```
.
├── backend/
│   ├── core/              # Django project settings
│   ├── runner/            # Main Django app
│   │   ├── api/           # REST API (views, serializers, urls)
│   │   ├── models/        # Database models
│   │   ├── services/      # Business logic layer
│   │   ├── forms/         # Django forms
│   │   ├── management/    # Custom management commands
│   │   └── tests/         # Test files
│   ├── docker/            # Docker VM bootstrap utilities
│   ├── manage.py          # Django management script
│   ├── requirements.txt   # Python dependencies
│   └── pytest.ini         # Pytest configuration
├── frontend/
│   ├── src/
│   │   ├── api/           # API client
│   │   ├── components/    # Reusable Vue components
│   │   ├── pages/         # Page-level components
│   │   ├── router/        # Vue Router configuration
│   │   ├── stores/        # Pinia stores
│   │   └── App.vue        # Root component
│   └── package.json       # NPM dependencies
├── data/                  # Problem sets and contest data
└── docker-compose.yml     # Local development setup
```

## Development Workflow

### Running the Application

**With Docker Compose (Recommended)**:
```bash
docker-compose up
```
- Backend: http://localhost:8100
- Frontend: http://localhost:8101
- Jupyter Notebooks: http://localhost:8888

**Backend Only**:
```bash
cd backend
python -m pip install -r requirements.txt
python manage.py migrate
python manage.py runserver 8100
```

**Frontend Only**:
```bash
cd frontend
npm install
npm run serve
```

### Testing

**Backend Tests**:
```bash
cd backend
python manage.py test -v 2        # Django test runner
# OR
pytest                             # Pytest runner
```

**Frontend Linting**:
```bash
cd frontend
npm run lint
```

### CI/CD

The project uses GitHub Actions:
- **Workflow**: `.github/workflows/django.yml`
- **Triggers**: Push/PR to `main` branch
- **Tests**: Runs Django tests with PostgreSQL 16

## Coding Conventions

### Python/Django

1. **Service Layer Pattern**: Business logic goes in `runner/services/`, not in views or models
2. **Type Hints**: Use Python type hints for function signatures
3. **Import Order**: Standard library → Third-party → Django → Local imports
4. **Model Managers**: Custom querysets and managers in `runner/models/`
5. **API Structure**: 
   - Serializers in `runner/api/serializers/`
   - Views in `runner/api/views/`
   - URL patterns in `runner/api/urls.py`
6. **Testing**: Test files follow pattern `test_*.py` in appropriate directories

### Vue.js/Frontend

1. **Component Structure**: Template → Script → Style
2. **Naming**: 
   - Components use PascalCase (e.g., `HomePage.vue`, `UiHeader`)
   - Props and events use kebab-case in templates
3. **State Management**: Use Pinia stores for global state
4. **API Calls**: Centralized in `src/api/`
5. **Routing**: Page components in `src/pages/`, routes in `src/router/`

## Key Technologies

### Backend
- **Authentication**: JWT with djangorestframework-simplejwt
- **CORS**: django-cors-headers
- **WebSockets**: Django Channels
- **Task Queue**: Celery with Redis broker
- **Code Execution**: Jupyter kernels running in Docker containers
- **Testing**: Django test framework + pytest-django

### Frontend
- **State**: Pinia
- **HTTP Client**: Axios
- **Markdown**: markdown-it with KaTeX support for math rendering
- **Routing**: Vue Router 4

## Environment Configuration

The application uses environment variables (`.env` files):

**Backend** (see `backend/.env.template`):
- `MODE`: `dev`, `test`, or `prod`
- `DB_*`: Database connection settings
- `SECRET_KEY`: Django secret key
- `DEBUG`: Enable/disable debug mode
- `CELERY_BROKER_URL`: Redis URL for Celery
- `RUNTIME_*`: Code execution environment settings

**Frontend**:
- `VUE_APP_API_BASE`: API base path
- `VUE_APP_BACKEND_URL`: Backend URL

## Special Considerations

1. **Code Execution Security**: The platform executes user-submitted code in isolated Docker containers managed through `runner/services/runtime/`

2. **Real-time Updates**: Use Django Channels consumers for WebSocket connections (submission status, cell execution results)

3. **Database Migrations**: Always create and test migrations for model changes:
   ```bash
   python manage.py makemigrations
   python manage.py migrate
   ```

4. **Media Files**: User-generated content (notebooks, submission files) stored in `backend/media/`

5. **Test Data**: Sample problems and contests in `data/` directory (markdown format)

## Common Tasks

### Adding a New API Endpoint

1. Create serializer in `backend/runner/api/serializers/`
2. Create view in `backend/runner/api/views/`
3. Add URL pattern in `backend/runner/api/urls.py`
4. Write tests in `backend/runner/api/views/test_*.py`
5. Add corresponding API client method in `frontend/src/api/`

### Adding a New Model

1. Define model in `backend/runner/models/`
2. Create migration: `python manage.py makemigrations`
3. Apply migration: `python manage.py migrate`
4. Register in admin if needed: `backend/runner/admin.py`
5. Write model tests in `backend/runner/models/test_*.py`

### Adding a New Page

1. Create Vue component in `frontend/src/pages/`
2. Add route in `frontend/src/router/`
3. Create any needed API endpoints in backend
4. Add corresponding store if complex state needed

## Resources

- [Django Documentation](https://docs.djangoproject.com/)
- [Django REST Framework](https://www.django-rest-framework.org/)
- [Vue 3 Documentation](https://vuejs.org/)
- [Pinia Documentation](https://pinia.vuejs.org/)
