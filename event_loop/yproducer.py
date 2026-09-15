import heapq
import time
from collections import deque


class Scheduler:
    def __init__(self):
        self.ready = deque()
        self.sleeping = []
        self.sequence = 0
        self.current = None  # Currently executing generator

    async def sleep(self, delay):
        deadline = time.time() + delay
        self.sequence += (
            1  # tie breaker for case [(2, coro at add...), (2, coro at add...)]
        )
        heapq.heappush(self.sleeping, (deadline, self.sequence, self.current))
        self.current = None
        await switch()  # switch tasks

    def new_task(self, coro):
        self.ready.append(coro)

    def run(self):
        while self.ready or self.sleeping:
            if not self.ready:
                deadline, _, coro = heapq.heappop(self.sleeping)
                delta = deadline - time.time()
                if delta > 0:
                    time.sleep(delta)
                self.ready.append(coro)
            else:
                self.current = self.ready.popleft()
                # Drive as a generator
                try:
                    self.current.send(None)  # Send to coroutine
                    if self.current:
                        self.ready.append(self.current)
                except StopIteration:
                    ...


sched = Scheduler()


class Awaitable:
    def __await__(self):
        yield


def switch():
    return Awaitable()

# ---------------------

class AsyncQueue:
    def __init__(self):
        self.items = deque()
        self.waiting = deque()

    async def put(self, item):
        self.items.append(item)
        if self.waiting:
            sched.ready.append(self.waiting.popleft())

    async def get(self):
        if not self.items:
            self.waiting.append(sched.current)  # Put myself to sleep
            sched.current = None                # "Disappear"
            await switch()                      # Switch to another task
        return self.items.popleft()

async def producer(q, count):
    for n in range(count):
        print(f"Producing {n}")
        await q.put(n)
        await sched.sleep(1)
    print("Producer done")
    await q.put(None)


async def consumer(q):
    while True:
        item = await q.get()
        if item is None:
            break
        print(f"Consuming {item}")
    print("Consumer done")


q = AsyncQueue()
sched.new_task(producer(q, 10))
sched.new_task(consumer(q))
sched.run()
