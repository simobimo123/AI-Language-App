import time
from collections import defaultdict, deque

from fastapi import HTTPException


RATE_LIMIT_REQUESTS = 10
RATE_LIMIT_WINDOW_SECONDS = 60

_user_requests: dict[int, deque[float]] = defaultdict(deque)


def check_rate_limit(user_id: int) -> None:
    now = time.monotonic()
    requests = _user_requests[user_id]

    while requests and now - requests[0] >= RATE_LIMIT_WINDOW_SECONDS:
        requests.popleft()

    if len(requests) >= RATE_LIMIT_REQUESTS:
        raise HTTPException(
            status_code=429,
            detail=(
                "Too many AI requests. "
                "Please wait before trying again."
            ),
        )

    requests.append(now)


