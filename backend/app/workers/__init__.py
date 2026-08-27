"""Trading worker processes.

The trading worker runs independently of the FastAPI HTTP process so that
restarting the API cannot start, stop, or duplicate trading activity.
"""
