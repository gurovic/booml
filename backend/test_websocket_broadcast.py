#!/usr/bin/env python
"""
Test script to manually trigger a broadcast and verify WebSocket is working.
Run this from the Django shell or as a management command.

Usage:
    python manage.py shell < test_websocket_broadcast.py

Or in Django shell:
    from runner.services.websocket_notifications import broadcast_submission_update
    broadcast_submission_update(problem_id=1, submission_id=999, status="accepted", metrics={"test": 0.95})
"""

from runner.services.websocket_notifications import broadcast_submission_update

# Test broadcast
print("Testing WebSocket broadcast...")
print("=" * 60)

problem_id = 1
submission_id = 999
status = "accepted"
metrics = {"accuracy": 0.95, "test": True}

print(f"Broadcasting test update:")
print(f"  problem_id: {problem_id}")
print(f"  submission_id: {submission_id}")
print(f"  status: {status}")
print(f"  metrics: {metrics}")
print()

broadcast_submission_update(
    problem_id=problem_id,
    submission_id=submission_id,
    status=status,
    metrics=metrics,
)

print()
print("Broadcast sent! Check:")
print("1. Backend logs for 'Broadcasting submission update'")
print("2. Browser console for WebSocket messages")
print("3. Network tab in DevTools for WebSocket frames")
