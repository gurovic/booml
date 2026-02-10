# WebSocket Testing Guide - Automatic Submission Updates

This document describes how to test the automatic submission list updates via WebSocket.

## Overview

The system now supports real-time updates of submission lists. When a submission's status changes (e.g., from "pending" to "accepted"), all users viewing that problem's submissions page will see the update automatically without refreshing.

## Architecture

### Backend Components

1. **ProblemSubmissionsConsumer** (`backend/runner/services/consumers.py`)
   - WebSocket consumer that handles connections to `/ws/problems/<problem_id>/submissions/`
   - Subscribes clients to a group: `problem_submissions_{problem_id}`
   - Sends `submission_update` events to connected clients

2. **broadcast_submission_update()** (`backend/runner/services/websocket_notifications.py`)
   - Utility function to broadcast submission updates to all subscribers
   - Called when a submission's status or metrics change

3. **evaluate_submission()** (`backend/runner/services/worker.py`)
   - Celery task that processes submissions
   - Calls `broadcast_submission_update()` after updating submission status

### Frontend Component

**SubmissionListPage.vue** (`frontend/src/pages/SubmissionListPage.vue`)
- Establishes WebSocket connection when component mounts
- Listens for `submission_update` events
- Updates the submission list in real-time
- Properly closes WebSocket connection on unmount

## How to Test Locally

### 1. Start the Development Environment

```bash
# Start all services (PostgreSQL, Redis, Backend, Frontend, Celery)
docker-compose up
```

This will start:
- Backend on http://localhost:8100
- Frontend on http://localhost:8101
- PostgreSQL on localhost:5432
- Redis on localhost:6379

### 2. Open the Submission List Page

1. Navigate to http://localhost:8101
2. Log in with your credentials
3. Go to a problem page
4. Navigate to the submissions list page (e.g., `/problem/1/submissions/`)

### 3. Test Automatic Updates

#### Option A: Submit a New Solution

1. While keeping the submissions page open, submit a new solution to the problem
2. You should see the new submission appear in the list automatically
3. Watch as the status changes from "⏳ В очереди" → "🏃 Выполняется" → "✅ Протестировано" or "❌ Ошибка"
4. The metrics should also appear automatically when the evaluation completes

#### Option B: Monitor Existing Submissions

1. Open the submissions page for a problem that has pending submissions
2. Open the browser's Developer Console (F12)
3. Look for WebSocket connection logs: "WebSocket connected for problem submissions"
4. Watch as submissions automatically update their status

### 4. Verify WebSocket Connection

Open the browser's Network tab in Developer Tools:

1. Filter by "WS" (WebSocket)
2. You should see a connection to `ws://localhost:8100/ws/problems/<problem_id>/submissions/`
3. When a submission updates, you should see messages in the WebSocket frame

Example message:
```json
{
  "type": "submission_update",
  "submission_id": 42,
  "status": "accepted",
  "metrics": {
    "accuracy": 0.95,
    "f1": 0.87
  }
}
```

## Testing with Multiple Clients

1. Open the same submissions page in multiple browser tabs/windows
2. Submit a new solution in one tab
3. Verify that all tabs receive the update simultaneously

## Troubleshooting

### WebSocket Connection Fails

**Check Redis:**
```bash
docker-compose logs redis
```
Redis must be running for Channel layers to work.

**Check Channel Layer Configuration:**
In `backend/core/settings.py`, verify:
```python
CHANNEL_LAYER_REDIS_URL = "redis://redis:6379/2"
```

### Updates Not Appearing

**Check Celery Worker:**
```bash
docker-compose logs celery
```
Make sure the Celery worker is running and processing tasks.

**Check Backend Logs:**
```bash
docker-compose logs backend
```
Look for WebSocket connection logs and broadcast messages.

### Console Errors

Open browser console (F12) and check for:
- WebSocket connection errors
- JSON parse errors
- Network issues

## Manual Testing with wscat

You can test the WebSocket endpoint directly using `wscat`:

```bash
# Install wscat
npm install -g wscat

# Connect to the WebSocket
wscat -c ws://localhost:8100/ws/problems/1/submissions/

# You should see connection success and receive updates
```

## Environment Variables

Make sure these are set in your docker-compose.yml:

```yaml
CHANNEL_LAYER_REDIS_URL: redis://redis:6379/2
CELERY_BROKER_URL: redis://redis:6379/0
CELERY_RESULT_BACKEND: redis://redis:6379/1
RUNNER_USE_CELERY_QUEUE: 1
```

## Code References

- Backend Consumer: `backend/runner/services/consumers.py` (class `ProblemSubmissionsConsumer`)
- Backend Routing: `backend/runner/services/routing.py`
- Backend Broadcast: `backend/runner/services/websocket_notifications.py` (function `broadcast_submission_update`)
- Backend Worker: `backend/runner/services/worker.py` (function `evaluate_submission`)
- Frontend Page: `frontend/src/pages/SubmissionListPage.vue`

## Notes

- The WebSocket connection is automatically established when viewing a problem's submissions
- The connection is properly closed when leaving the page
- Multiple users can connect simultaneously to the same problem's submission updates
- Updates are broadcast to all connected clients in real-time
- The system gracefully handles connection failures and will log errors to the console
