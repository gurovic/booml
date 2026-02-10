# WebSocket Troubleshooting Guide

## Problem: Submissions not updating in real-time

This guide will help you diagnose and fix WebSocket connection issues.

## Step 1: Check Docker Logs

### Backend Logs
```bash
docker-compose logs -f backend | grep -i "websocket\|broadcast\|submission"
```

Look for:
- `Broadcasting submission update: submission_id=X, problem_id=Y, status=accepted`
- `Successfully broadcasted submission update to problem_submissions_Y`

If you DON'T see these logs when a submission completes:
- The broadcast function is not being called
- Check that `submission.problem_id` is not None
- Check the worker logs

### Celery Worker Logs
```bash
docker-compose logs -f celery | grep -i "submission\|evaluation"
```

Look for:
- `[WORKER] Evaluating submission X`
- `[WORKER] Submission X evaluation finished: accepted`

### Redis Logs
```bash
docker-compose logs redis
```

Ensure Redis is running without errors.

## Step 2: Check WebSocket Connection in Browser

1. Open the submissions page: `http://localhost:8101/problem/1/submissions/`
2. Open Developer Tools (F12)
3. Go to Console tab

Look for:
- `[WebSocket] Attempting to connect to: ws://localhost:8100/ws/problems/1/submissions/`
- `[WebSocket] Connected successfully for problem submissions`

If connection fails:
- Check that the backend is running on port 8100
- Check that Django Channels is properly configured
- Check that Redis is running

## Step 3: Monitor WebSocket Messages

In Developer Tools:
1. Go to Network tab
2. Filter by "WS" (WebSocket)
3. Click on the WebSocket connection
4. Go to "Messages" sub-tab

You should see messages when submissions are processed:
```json
{
  "type": "submission_update",
  "submission_id": 42,
  "status": "accepted",
  "metrics": {"accuracy": 0.95}
}
```

## Step 4: Test Manual Broadcast

Run this in Django shell to test the broadcast:

```bash
docker-compose exec backend python manage.py shell
```

Then:
```python
from runner.services.websocket_notifications import broadcast_submission_update
broadcast_submission_update(problem_id=1, submission_id=999, status="accepted", metrics={"test": 0.95})
```

Check browser console - you should see the update arrive.

## Step 5: Verify Channel Layer Configuration

Check `backend/core/settings.py`:
```python
CHANNEL_LAYER_REDIS_URL = os.getenv("CHANNEL_LAYER_REDIS_URL", "").strip()
```

Check `docker-compose.yml`:
```yaml
CHANNEL_LAYER_REDIS_URL: redis://redis:6379/2
```

Test Channel Layer in Django shell:
```python
from channels.layers import get_channel_layer
channel_layer = get_channel_layer()
print(f"Channel layer: {channel_layer}")
print(f"Is None: {channel_layer is None}")
```

If channel_layer is None:
- Redis is not configured
- Check CHANNEL_LAYER_REDIS_URL environment variable

## Common Issues and Fixes

### Issue 1: "Skip websocket broadcast: channel layer is not configured"

**Cause:** Redis Channel Layer is not configured or Redis is not running

**Fix:**
1. Check Redis is running: `docker-compose ps redis`
2. Check environment variable: `CHANNEL_LAYER_REDIS_URL=redis://redis:6379/2`
3. Restart services: `docker-compose restart backend celery`

### Issue 2: "Skip websocket broadcast: problem id is missing"

**Cause:** Submission has no problem_id

**Fix:**
1. Ensure submissions are created with a valid problem_id
2. Check the submission creation code
3. Verify the problem exists

### Issue 3: WebSocket connection refused

**Cause:** Backend is not serving WebSocket connections

**Fix:**
1. Ensure Django Channels is installed: `pip list | grep channels`
2. Check ASGI configuration in `backend/core/asgi.py`
3. Verify routing in `backend/runner/services/routing.py`
4. Restart backend: `docker-compose restart backend`

### Issue 4: Messages not appearing in browser

**Cause:** Frontend not handling messages correctly

**Fix:**
1. Check browser console for JavaScript errors
2. Verify WebSocket connection is established
3. Check that message handler is registered
4. Verify submission is in the current page

### Issue 5: Updates work for some statuses but not others

**Cause:** Broadcast is not called for all status changes

**Fix:**
1. Check worker.py that broadcast is called after ALL status updates
2. Verify error handling also broadcasts
3. Check logs for any exceptions

## Debugging Checklist

- [ ] Redis is running
- [ ] Backend container is running
- [ ] Celery worker is running
- [ ] CHANNEL_LAYER_REDIS_URL is set correctly
- [ ] WebSocket URL matches backend URL (port 8100)
- [ ] Browser console shows WebSocket connection
- [ ] Backend logs show broadcast messages
- [ ] Worker logs show submission processing
- [ ] Manual broadcast test works
- [ ] Channel layer is not None in Django shell

## Testing Commands

### Check Redis connectivity
```bash
docker-compose exec redis redis-cli ping
# Should return: PONG
```

### Check if backend can reach Redis
```bash
docker-compose exec backend python -c "
from channels.layers import get_channel_layer
cl = get_channel_layer()
print('Channel layer:', cl)
print('Config:', cl.hosts if hasattr(cl, 'hosts') else 'N/A')
"
```

### Restart all services
```bash
docker-compose restart backend celery redis
```

### View real-time logs
```bash
# Terminal 1: Backend
docker-compose logs -f backend

# Terminal 2: Celery
docker-compose logs -f celery

# Terminal 3: Redis
docker-compose logs -f redis
```

## Still Not Working?

If after all these steps it's still not working:

1. Check Django version compatibility with Channels
2. Check if there are any firewall issues
3. Try with a different problem_id
4. Check if there are any middleware blocking WebSocket
5. Review the implementation against Django Channels documentation

## Success Indicators

When everything is working correctly, you should see:

1. **Backend logs:**
   ```
   [INFO] Broadcasting submission update: submission_id=42, problem_id=1, status=accepted
   [INFO] Successfully broadcasted submission update to problem_submissions_1
   ```

2. **Browser console:**
   ```
   [WebSocket] Connected successfully for problem submissions
   [WebSocket] Message received: {"type":"submission_update",...}
   [WebSocket] Updating submission 42: status=accepted
   [WebSocket] Updated submission state: {...}
   ```

3. **Network tab:**
   - WebSocket connection shown in green
   - Messages visible in Messages sub-tab
   - No error frames

4. **UI:**
   - Submission status updates automatically
   - No page refresh needed
   - Metrics appear when evaluation completes
