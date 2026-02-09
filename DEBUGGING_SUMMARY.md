# Отладка проблемы: Список посылок не обновляется

## Проблема
"Список последних посылок не обновляется при статусе Протестировано"

## Проведённый анализ

### Потенциальные причины
1. ❓ WebSocket соединение не устанавливается
2. ❓ Broadcast функция не вызывается
3. ❓ Сообщения не доходят до клиента
4. ⚠️ **Vue реактивность не срабатывает** (ИСПРАВЛЕНО)
5. ❓ Channel Layer не настроен

## Реализованные исправления

### 1. Исправлена Vue реактивность ✅

**Проблема:** Прямое присваивание по индексу массива может не отслеживаться Vue

**Было:**
```javascript
submissions.value[index] = {
  ...submissions.value[index],
  status,
  metrics
}
```

**Стало:**
```javascript
const updatedSubmission = {
  ...submissions.value[index],
  status,
  metrics
}
submissions.value.splice(index, 1, updatedSubmission)
```

**Результат:** Использование `splice()` гарантирует, что Vue отследит изменение массива

### 2. Добавлено подробное логирование ✅

**Backend (`websocket_notifications.py`):**
- Логирование перед отправкой broadcast
- Логирование после успешной отправки
- Логирование ошибок
- Информация о problem_id, submission_id, status, group_name

**Backend (`consumers.py`):**
- Логирование подключения клиента
- Логирование получения сообщений
- Логирование отправки обновлений клиенту
- Логирование отключения клиента

**Frontend (`SubmissionListPage.vue`):**
- Логирование попытки подключения
- Логирование успешного подключения
- Логирование всех входящих сообщений
- Логирование обработки обновлений
- Логирование поиска посылки в списке

### 3. Добавлена проверка problem_id ✅

**Проблема:** Некоторые посылки могут иметь `problem_id = null`

**Решение:**
```python
if submission.problem_id:
    broadcast_submission_update(...)
else:
    logger.warning(f"Submission has no problem_id, skipping broadcast")
```

### 4. Оптимизирован запрос к БД ✅

**Добавлено:** `select_related('problem')` для избежания N+1 запросов

```python
submission = Submission.objects.select_related('problem').get(pk=submission_id)
```

### 5. Создана тестовая HTML страница ✅

**Файл:** `backend/static/websocket_test.html`

**Возможности:**
- Подключение к WebSocket напрямую
- Настройка problem_id
- Просмотр всех входящих сообщений
- Отключение от WebSocket
- Очистка лога

**Использование:**
```
http://localhost:8100/static/websocket_test.html
```

### 6. Создан тестовый скрипт ✅

**Файл:** `backend/test_websocket_broadcast.py`

**Использование:**
```bash
docker-compose exec backend python manage.py shell < test_websocket_broadcast.py
```

Или в Django shell:
```python
from runner.services.websocket_notifications import broadcast_submission_update
broadcast_submission_update(
    problem_id=1,
    submission_id=999,
    status="accepted",
    metrics={"test": 0.95}
)
```

### 7. Создан гайд по отладке ✅

**Файл:** `WEBSOCKET_TROUBLESHOOTING.md`

**Содержит:**
- Пошаговую диагностику
- Проверку логов Docker
- Проверку WebSocket соединения
- Мониторинг сообщений
- Тест ручного broadcast
- Проверку Channel Layer
- Список частых проблем с решениями

## Инструкции по тестированию

### Вариант 1: Тестовая HTML страница (рекомендуется)

1. Запустить приложение:
   ```bash
   docker-compose up
   ```

2. Открыть тестовую страницу:
   ```
   http://localhost:8100/static/websocket_test.html
   ```

3. Нажать "Connect"

4. В другой вкладке отправить посылку или запустить тест:
   ```bash
   docker-compose exec backend python manage.py shell
   ```
   ```python
   from runner.services.websocket_notifications import broadcast_submission_update
   broadcast_submission_update(problem_id=1, submission_id=999, status="accepted", metrics={"accuracy": 0.95})
   ```

5. Проверить, что сообщение появилось на тестовой странице

**Если сообщения приходят** → WebSocket работает, проблема была в Vue реактивности (исправлено)
**Если сообщения НЕ приходят** → Проблема в backend/Channel Layer/Redis

### Вариант 2: Основное приложение

1. Запустить приложение:
   ```bash
   docker-compose up
   ```

2. Открыть основное приложение:
   ```
   http://localhost:8101
   ```

3. Войти в систему и перейти на страницу посылок задачи

4. Открыть Developer Tools (F12) → Console

5. Отправить посылку или дождаться обработки существующей

6. Проверить логи в консоли:
   ```
   [WebSocket] Attempting to connect to: ws://localhost:8100/ws/problems/1/submissions/
   [WebSocket] Connected successfully for problem submissions
   [WebSocket] Message received: {...}
   [WebSocket] Updating submission X: status=accepted
   ```

### Вариант 3: Проверка логов

**Backend:**
```bash
docker-compose logs -f backend | grep -i "broadcasting\|problemsubmissions"
```

Ожидаемый вывод:
```
Broadcasting submission update: submission_id=42, problem_id=1, status=accepted, group=problem_submissions_1
Successfully broadcasted submission update to problem_submissions_1
ProblemSubmissionsConsumer: Client connected to problem_submissions_1
ProblemSubmissionsConsumer: Received submission_update: {...}
ProblemSubmissionsConsumer: Sent update to client for submission 42
```

**Celery:**
```bash
docker-compose logs -f celery | grep -i "worker.*submission"
```

Ожидаемый вывод:
```
[WORKER] Evaluating submission 42
[WORKER] Submission 42 evaluation finished: accepted
```

## Возможные остаточные проблемы

### Если после всех исправлений проблема сохраняется:

1. **Channel Layer не настроен:**
   - Проверить: `CHANNEL_LAYER_REDIS_URL` в docker-compose.yml
   - Проверить: Redis запущен и доступен
   - Тест в Django shell:
     ```python
     from channels.layers import get_channel_layer
     print(get_channel_layer())  # Не должно быть None
     ```

2. **WebSocket не может подключиться:**
   - Проверить CORS настройки
   - Проверить, что backend работает на порту 8100
   - Проверить routing в `runner/services/routing.py`
   - Проверить ASGI в `core/asgi.py`

3. **Broadcast не вызывается:**
   - Проверить логи worker
   - Убедиться, что `submission.problem_id` не None
   - Проверить, что Celery worker запущен

4. **Frontend не обрабатывает обновления:**
   - Проверить консоль браузера на ошибки JavaScript
   - Убедиться, что posylka находится в текущей странице
   - Проверить, что handleSubmissionUpdate вызывается

## Текущий статус

✅ Исправлена Vue реактивность (использование splice)
✅ Добавлено подробное логирование
✅ Добавлена проверка problem_id
✅ Создана тестовая страница
✅ Создан тестовый скрипт
✅ Создан гайд по отладке

**Следующий шаг:** Пользователю нужно протестировать исправления и предоставить логи, если проблема сохраняется.

## Команды для сбора диагностики

Если проблема сохраняется после исправлений, запустите эти команды и предоставьте вывод:

```bash
# 1. Проверить статус сервисов
docker-compose ps

# 2. Проверить логи backend
docker-compose logs backend | grep -i "broadcasting\|websocket\|channel" | tail -50

# 3. Проверить логи Celery
docker-compose logs celery | grep -i "submission" | tail -30

# 4. Проверить Redis
docker-compose logs redis | tail -20

# 5. Проверить Channel Layer в Django
docker-compose exec backend python -c "
from channels.layers import get_channel_layer
cl = get_channel_layer()
print('Channel Layer:', cl)
print('Type:', type(cl))
if hasattr(cl, 'hosts'):
    print('Redis hosts:', cl.hosts)
"

# 6. Протестировать broadcast вручную
docker-compose exec backend python manage.py shell -c "
from runner.services.websocket_notifications import broadcast_submission_update
broadcast_submission_update(problem_id=1, submission_id=999, status='accepted', metrics={'test': 0.95})
print('Broadcast sent! Check browser console.')
"
```

## Заключение

Основное исправление - замена прямого присваивания по индексу массива на метод `splice()` для гарантии Vue реактивности. Дополнительно добавлено всестороннее логирование и инструменты для диагностики, чтобы пользователь мог точно определить, на каком этапе возникает проблема, если она сохранится.
