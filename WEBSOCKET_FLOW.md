# WebSocket Flow Diagram

## Автоматическое обновление списка посылок

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         User opens submissions page                      │
│                      /problem/{problem_id}/submissions/                  │
└─────────────────────────────────────┬───────────────────────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                    Vue Component (SubmissionListPage.vue)                │
│  ┌────────────────────────────────────────────────────────────────────┐ │
│  │  onMounted:                                                         │ │
│  │  1. Fetch initial submission list via REST API                     │ │
│  │  2. Connect to WebSocket:                                          │ │
│  │     ws://host/ws/problems/{problem_id}/submissions/                │ │
│  └────────────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────┬───────────────────────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────────────┐
│              Backend: ProblemSubmissionsConsumer (Django Channels)       │
│  ┌────────────────────────────────────────────────────────────────────┐ │
│  │  connect():                                                         │ │
│  │  1. Parse problem_id from URL                                      │ │
│  │  2. Join group: "problem_submissions_{problem_id}"                 │ │
│  │  3. Accept WebSocket connection                                    │ │
│  └────────────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────────────┘
                                      │
                                      │ WebSocket Connection Established
                                      │
                  ┌───────────────────┴──────────────────┐
                  │                                       │
                  ▼                                       ▼
    ┌────────────────────────┐            ┌────────────────────────┐
    │   User submits new     │            │   Background Celery    │
    │   solution via UI      │            │   worker processing    │
    └───────────┬────────────┘            │   existing submission  │
                │                          └───────────┬────────────┘
                ▼                                      │
    ┌────────────────────────┐                        │
    │ SubmissionCreateView   │                        │
    │ (REST API)             │                        │
    │ 1. Save submission     │                        │
    │ 2. Pre-validation      │                        │
    │ 3. Enqueue for eval    │                        │
    └───────────┬────────────┘                        │
                │                                      │
                └──────────────┬───────────────────────┘
                               │
                               ▼
                ┌─────────────────────────────────────────┐
                │   Celery Task: evaluate_submission()    │
                │  (backend/runner/services/worker.py)    │
                │  ┌───────────────────────────────────┐  │
                │  │ 1. Run checker on submission     │  │
                │  │ 2. Update status and metrics     │  │
                │  │ 3. Save to database              │  │
                │  │ 4. Call broadcast_submission_    │  │
                │  │    update()                      │  │
                │  └───────────────────────────────────┘  │
                └──────────────────┬──────────────────────┘
                                   │
                                   ▼
                ┌─────────────────────────────────────────┐
                │  broadcast_submission_update()          │
                │  (websocket_notifications.py)           │
                │  ┌───────────────────────────────────┐  │
                │  │ Send to Channel Layer:           │  │
                │  │ {                                │  │
                │  │   type: "submission.update"      │  │
                │  │   submission_id: 42              │  │
                │  │   status: "accepted"             │  │
                │  │   metrics: {...}                 │  │
                │  │ }                                │  │
                │  │ Target: "problem_submissions_1"  │  │
                │  └───────────────────────────────────┘  │
                └──────────────────┬──────────────────────┘
                                   │
                                   │ Redis Channel Layer
                                   │
                                   ▼
                ┌─────────────────────────────────────────┐
                │  ProblemSubmissionsConsumer             │
                │  submission_update() handler            │
                │  ┌───────────────────────────────────┐  │
                │  │ Send JSON to WebSocket:          │  │
                │  │ {                                │  │
                │  │   type: "submission_update"      │  │
                │  │   submission_id: 42              │  │
                │  │   status: "accepted"             │  │
                │  │   metrics: {...}                 │  │
                │  │ }                                │  │
                │  └───────────────────────────────────┘  │
                └──────────────────┬──────────────────────┘
                                   │
                                   │ WebSocket Message
                                   │
                                   ▼
                ┌─────────────────────────────────────────┐
                │  Vue Component (SubmissionListPage.vue) │
                │  ┌───────────────────────────────────┐  │
                │  │ ws.onmessage():                  │  │
                │  │ 1. Parse JSON message            │  │
                │  │ 2. Find submission in list       │  │
                │  │ 3. Update status and metrics     │  │
                │  │ 4. UI automatically updates!     │  │
                │  └───────────────────────────────────┘  │
                └─────────────────────────────────────────┘
                                   │
                                   ▼
                ┌─────────────────────────────────────────┐
                │   User sees updated submission          │
                │   WITHOUT refreshing the page! ✨       │
                └─────────────────────────────────────────┘
```

## Key Components

### Backend
1. **ProblemSubmissionsConsumer** - WebSocket handler
2. **broadcast_submission_update()** - Sends updates to all subscribers
3. **evaluate_submission()** - Celery task that triggers broadcasts
4. **Redis** - Channel layer for message passing

### Frontend
1. **SubmissionListPage.vue** - UI component with WebSocket client
2. **WebSocket connection** - Listens for real-time updates
3. **handleSubmissionUpdate()** - Updates UI when message received

## Benefits

✅ **Real-time updates** - No need to refresh the page  
✅ **Multiple users** - All users see updates simultaneously  
✅ **Automatic reconnection** - Handled by browser WebSocket API  
✅ **Scalable** - Redis Channel Layer can handle many connections  
✅ **Clean architecture** - Separation of concerns between components  
