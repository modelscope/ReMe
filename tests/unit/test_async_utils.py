"""Side-effecting thread calls retain ownership through cancellation."""

import asyncio
import threading

import pytest

from reme.utils.async_utils import complete_in_thread


@pytest.mark.asyncio
@pytest.mark.parametrize("cancellations", [0, 1, 3])
@pytest.mark.parametrize("fail", [False, True])
async def test_complete_in_thread_finishes_before_propagating_result(cancellations, fail):
    """Repeated cancellation waits for success or failure without detaching work."""
    started, release, finished = threading.Event(), threading.Event(), threading.Event()

    def operation():
        started.set()
        try:
            assert release.wait(5)
            if fail:
                raise RuntimeError("thread failed")
            return "complete"
        finally:
            finished.set()

    task = asyncio.create_task(complete_in_thread(operation))
    try:
        assert await asyncio.to_thread(started.wait, 5)
        for _ in range(cancellations):
            task.cancel()
            await asyncio.sleep(0)
        assert not task.done()
        assert not finished.is_set()
    finally:
        release.set()
        await asyncio.gather(task, return_exceptions=True)

    assert finished.is_set()
    if cancellations:
        with pytest.raises(asyncio.CancelledError):
            task.result()
    elif fail:
        with pytest.raises(RuntimeError, match="thread failed"):
            task.result()
    else:
        assert task.result() == "complete"
