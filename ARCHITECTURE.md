# Архитектура проекта booml

**booml** — платформа для обучения машинному обучению: студенты решают задачи в браузере (Jupyter-совместимые ноутбуки), отправляют решения на проверку и отслеживают прогресс в курсах и контестах.

---

## Компоненты системы

```mermaid
flowchart TD
    subgraph Client["Браузер (клиент)"]
        FE["Vue 3 SPA\n(Vue Router · Pinia · Axios)"]
    end

    subgraph Backend["Backend (Django / ASGI)"]
        direction TB
        API["REST API\n(Django REST Framework)"]
        WS["WebSocket\n(Django Channels)"]
        SVC["Services\n(course · section · worker · validation\nruntime · vm_manager · permissions)"]
        MDL["Models\n(User · Profile · Course · Section\nContest · Problem · Submission\nNotebook · Cell · Report · Tag …)"]
        CELERY_APP["Celery App\n(tasks.py)"]
    end

    subgraph Infra["Инфраструктура"]
        PG[("PostgreSQL 16")]
        REDIS[("Redis 7\n(broker · result · channel layer)")]
        WORKER["Celery Worker"]
        VM["runner-vm\n(Docker контейнер)"]
        KERNEL["Jupyter Kernel\n(Python · ML libraries)"]
    end

    %% Client ↔ Backend
    FE -- "HTTP/REST :8100" --> API
    FE -- "WS /ws/ :8100" --> WS

    %% API internal
    API --> SVC
    WS --> SVC
    SVC --> MDL
    MDL --> PG
    SVC --> CELERY_APP

    %% Async path
    CELERY_APP -- "enqueue" --> REDIS
    REDIS -- "consume" --> WORKER
    WORKER --> VM
    VM --> KERNEL

    %% Result notification
    KERNEL -- "execution result" --> WORKER
    WORKER -- "publish result" --> REDIS
    REDIS -- "channel layer" --> WS
    WS -- "push result" --> FE
```

---

## Уровни архитектуры

| Уровень | Технологии | Назначение |
|---|---|---|
| **Фронтенд** | Vue 3, Vue Router 4, Pinia, Axios, markdown-it + KaTeX | SPA: курсы, контесты, ноутбуки, результаты |
| **REST API** | Django REST Framework, simplejwt | CRUD ресурсов, аутентификация (JWT) |
| **WebSocket** | Django Channels, Redis channel layer | Стриминг вывода ячеек, уведомления |
| **Services** | Python (бизнес-логика) | Оценка решений, управление ВМ, права доступа |
| **Task Queue** | Celery, Redis broker | Асинхронное выполнение решений |
| **Runtime** | Docker (runner-vm), Jupyter kernels | Изолированное выполнение кода пользователей |
| **База данных** | PostgreSQL 16 | Хранение всех сущностей |
| **Кэш / брокер** | Redis 7 | Celery broker + result backend + channel layer |

---

## Ключевые потоки данных

### 1. Отправка решения (submission)

```mermaid
sequenceDiagram
    actor Student as Студент
    participant FE as Vue SPA
    participant API as REST API
    participant DB as PostgreSQL
    participant Q as Redis (broker)
    participant W as Celery Worker
    participant VM as Docker VM
    participant WS as WebSocket

    Student->>FE: нажимает «Отправить»
    FE->>API: POST /api/submissions/
    API->>DB: создать Submission (status=queued)
    API->>Q: enqueue задачу оценки
    API-->>FE: 201 Created {id}
    Q->>W: выдать задачу
    W->>VM: запустить код в изолированном контейнере
    VM-->>W: результат выполнения
    W->>DB: обновить Submission (status, score, report)
    W->>Q: publish через channel layer
    Q->>WS: уведомление
    WS-->>FE: push обновления статуса
    FE-->>Student: показать результат
```

### 2. Интерактивное выполнение ячейки ноутбука

```mermaid
sequenceDiagram
    actor Student as Студент
    participant FE as Vue SPA
    participant WS as WebSocket (Channels)
    participant SVC as Services / vm_manager
    participant VM as Docker VM (Jupyter Kernel)

    Student->>FE: запускает ячейку
    FE->>WS: send {action: run_cell, code: ...}
    WS->>SVC: запросить выполнение
    SVC->>VM: отправить код в ядро
    loop стриминг вывода
        VM-->>SVC: stdout / stderr chunk
        SVC-->>WS: relay chunk
        WS-->>FE: push chunk
    end
    VM-->>SVC: execution_complete
    SVC-->>WS: done
    WS-->>FE: {status: done}
    FE-->>Student: показать вывод
```

---

## Структура директорий

```
booml/
├── backend/
│   ├── core/               # Настройки Django, ASGI/WSGI
│   ├── runner/
│   │   ├── api/            # REST: сериализаторы, представления, urls.py
│   │   ├── models/         # ORM-модели
│   │   ├── services/       # Бизнес-логика, runtime, vm_manager, Channels-consumers
│   │   ├── forms/          # Django-формы
│   │   ├── management/     # Управляющие команды
│   │   └── tests/          # Тесты
│   ├── docker/             # Dockerfile и bootstrap для runner-vm
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── api/            # Axios-клиент
│   │   ├── components/     # Переиспользуемые компоненты
│   │   ├── pages/          # Страницы (Course, Contest, Notebook, …)
│   │   ├── router/         # Vue Router
│   │   ├── stores/         # Pinia stores
│   │   └── styles/         # Глобальные стили
│   └── package.json
├── data/                   # Наборы задач и контестов (Markdown)
└── docker-compose.yml
```
