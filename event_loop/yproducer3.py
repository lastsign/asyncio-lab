import heapq
import time
from collections import deque


class Scheduler:
    def __init__(self):
        self.ready = deque()
        self.sleeping = []
        self.sequence = 0
        self.clock = time.time

    def call_soon(self, func):
        self.ready.append(func)

    def call_later(self, delay, func):
        self.sequence += 1
        deadline = time.time() + delay
        heapq.heappush(self.sleeping, (deadline, self.sequence, func))

    def run(self):
        while self.ready or self.sleeping:
            if not self.ready:
                deadline, _, func = heapq.heappop(self.sleeping)
                delta = deadline - time.time()
                if delta > 0:
                    time.sleep(delta)
                self.ready.append(func)

            while self.ready:
                func = self.ready.popleft()
                func()

    def new_task(self, coro):
        self.ready.append(Task(coro))

    async def sleep(self, delay):
        self.call_later(delay, self.current)
        self.current = None
        await switch()


class Task:
    def __init__(self, coro):
        self.coro = coro

    # Make it look like a callback
    def __call__(self):
        try:
            # Driving the coroutine
            sched.current = self
            self.coro.send(None)
            if sched.current:
                sched.ready.append(self)
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
            sched.current = None  # "Disappear"
            await switch()  # Switch to another task
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


def count_down(x):
    if x > 0:
        print(f"Down {x}")
        sched.call_later(4, lambda: count_down(x - 1))


def count_up(stop):
    def _inner(x):
        if x < stop:
            print(f"Up {x}")
            sched.call_later(1, lambda: _inner(x + 1))

    _inner(0)


sched.call_soon(lambda: count_down(5))
sched.call_soon(lambda: count_up(20))

sched.run()
