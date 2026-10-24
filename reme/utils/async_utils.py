"""Small asyncio helpers."""

import asyncio
from collections.abc import Callable
from contextlib import suppress
from typing import Any


async def complete_in_thread(func: Callable[..., Any], /, *args) -> Any:
    """Finish a side-effecting thread call, including through repeated cancellation."""
    task = asyncio.create_task(asyncio.to_thread(func, *args))
    cancelled = False
    while not task.done():
        try:
            await asyncio.shield(task)
        except asyncio.CancelledError:
            cancelled = True
        except Exception:
            if not cancelled:
                raise
            break
    if cancelled:
        with suppress(Exception):
            task.result()
        raise asyncio.CancelledError
    return task.result()
