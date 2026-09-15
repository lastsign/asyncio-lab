import asyncio


async def easygoint():
    await asyncio.sleep(10)
    return "alive"


async def stubborn():
    try:
        await asyncio.sleep(10)
    except asyncio.CancelledError:
        asyncio.current_task().uncancel()
    await asyncio.sleep(0.1)
    return "Still alive"


async def main():
    task = asyncio.create_task(stubborn(), eager_start=True)

    task.cancel()

    print(await task)

    print(task.cancelled(), task.cancelling())


if __name__ == "__main__":
    asyncio.run(main())
