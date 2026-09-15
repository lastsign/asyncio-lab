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


async def count_down(x):
    while x > 0:
        print(f"Down {x}")
        await sched.sleep(4)
        x -= 1


async def count_up(stop):
    x = 0
    while x < stop:
        print(f"Up {x}")
        await sched.sleep(1)
        x += 1


sched.new_task(count_down(5))
sched.new_task(count_up(20))
sched.run()
