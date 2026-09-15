import asyncio

import pytest


async def succeed():
    await asyncio.sleep(0.1)


async def canceled():
    await asyncio.sleep(0)
    raise asyncio.CancelledError()


async def failed(delay=0.01):
    async with asyncio.timeout(delay):
        await asyncio.sleep(3)


@pytest.mark.asyncio
async def test_asyncio_gracefully_failed_task_in_gather():
    tasks = [succeed(), failed(), canceled()]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    assert len(results) == len(tasks)


@pytest.mark.asyncio
async def test_asyncio_failed_task_in_gather():
    with pytest.raises(asyncio.TimeoutError):
        await asyncio.gather(succeed(), failed())


@pytest.mark.asyncio
async def test_asyncio_canceled_task_in_gather():
    with pytest.raises(asyncio.CancelledError):
        await asyncio.gather(succeed(), canceled())


@pytest.mark.asyncio
async def test_asyncio_failed_canceled_tasks_in_gather():
    tasks = [succeed(), failed(), canceled()]
    with pytest.raises((asyncio.CancelledError, asyncio.TimeoutError)):
        await asyncio.gather(*tasks)
