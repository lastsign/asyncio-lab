import asyncio

import anyio
import pytest


async def easygoing():
    await asyncio.sleep(10)
    return "alive"


async def stubborn():
    try:
        await asyncio.sleep(10)
    except asyncio.CancelledError:
        asyncio.current_task().uncancel()
    await asyncio.sleep(0.1)
    return "alive"


async def slowpoke(delay):
    async with asyncio.timeout(delay):
        await asyncio.sleep(10)


async def anyio_stubborn():
    try:
        await anyio.sleep(10)
    except anyio.TaskCancelled:
        anyio.get_current_task()
    await anyio.sleep(0.1)


@pytest.mark.asyncio
async def test_asyncio_task_timeout_error_change():
    t = asyncio.create_task(slowpoke(0.01))

    with pytest.raises(TimeoutError):
        await t

    assert not t.cancelled()
    assert t.cancelling() == 0


@pytest.mark.asyncio
async def test_external_cancel_wins_over_timeout():
    t = asyncio.create_task(slowpoke(0), eager_start=True)
    t.cancel()

    with pytest.raises(asyncio.CancelledError):
        await t
    assert t.cancelled()
    assert t.cancelling() == 1


@pytest.mark.asyncio
@pytest.mark.parametrize("cancel", [1, 3, 10])
async def test_asyncio_task_cancelled(cancel):
    t = asyncio.create_task(easygoing(), eager_start=True)
    for _ in range(cancel):
        t.cancel()

    assert not t.done()
    assert not t.cancelled()
    assert t.cancelling() == cancel

    with pytest.raises(asyncio.CancelledError):
        await t

    assert t.done()
    assert t.cancelled()
    assert t.cancelling() == cancel
    assert t.uncancel() == cancel - 1


@pytest.mark.asyncio
@pytest.mark.parametrize("cancel", [1, 3, 10])
async def test_asyncio_task_cancelled_caught_but_never_raised_again(cancel):
    t = asyncio.create_task(stubborn(), eager_start=True)

    for _ in range(cancel):
        t.cancel()

    assert not t.done()
    assert not t.cancelled()
    assert t.cancelling() == cancel

    assert await t == "alive"

    assert t.done()
    assert not t.cancelled()
    assert t.cancelling() == cancel - 1
    assert t.uncancel() == max(cancel - 2, 0)


@pytest.mark.asyncio
async def test_asyncio_task_cancelled_before_execution():
    t = asyncio.create_task(stubborn())  # no eager_start=True
    t.cancel()  # no sleep, immediately cancel, even try wasn't open in stubborn
    with pytest.raises(asyncio.CancelledError):
        await t
    assert t.cancelled()
    assert t.cancelling() == 1


@pytest.mark.asyncio
async def test_asyncio_task_multiple_cancel_calls_collapse_in_one():
    t = asyncio.create_task(stubborn(), eager_start=True)

    for _ in range(3):
        t.cancel()

    assert await t == "alive"


# @pytest.mark.anyio
# @pytest.mark.parametrize("cancel", [1, 3, 10])
# async def test_anyio_task_cancelled(cancel):
#     async with anyio.create_task_group() as tg:
#         # with anyio.CancelScope() as scope:
#         t = tg.create_task(anyio_stubborn())
#         for _ in range(cancel):
#             t.cancel()

#         assert t.canceling()


# async def test_anyio_task_cancelling(): ...
