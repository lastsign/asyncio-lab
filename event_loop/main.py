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


sched = Scheduler()


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
