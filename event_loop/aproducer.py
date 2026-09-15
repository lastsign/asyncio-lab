import heapq
import time
from collections import deque


class QueueClosed(Exception): ...


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


class State:
    def __init__(self, value=None, exc=None):
        self.value = value
        self.exc = exc

    def result(self):
        if self.exc:
            raise self.exc
        else:
            return self.value


class AsyncQueue:
    def __init__(self):
        self.items = deque()
        self.waiting = deque()
        self._closed = False

    def close(self):
        self._closed = True
        if self.waiting and not self.items:
            for func in self.waiting:
                sched.call_soon(func)

    def put(self, item):
        if self._closed:
            raise QueueClosed()
        self.items.append(item)
        if self.waiting:
            func = self.waiting.popleft()
            sched.call_soon(func)

            # func() ---> might get deep calls, recursion, etc.

    def get(self, callback):
        # Wait until item is available. Then return it.
        # Question: How does a closed queue interact with get()
        if self.items:
            # Still run if "closed"
            # Good result
            callback(State(value=self.items.popleft()))
        else:
            # No items available (must wait)
            if self._closed:
                # Whats now?
                # Error result
                callback(State(exc=QueueClosed()))
            else:
                self.waiting.append(lambda: self.get(callback))


def producer(q, count):
    def _inner(n):
        if n < count:
            print(f"Producing {n}")
            q.put(n)
            sched.call_later(1, lambda: _inner(n + 1))
            time.sleep(1)
        else:
            print("Producer done")
            q.close()
            # q.put(None)

    _inner(0)


def consumer(q):
    def _consume(state):
        try:
            item = state.result()
            print(f"Consuming {item}")  # <----- Queue item (Result state)
            sched.call_soon(lambda: consumer(q))
        except QueueClosed:
            print("Consumer done")

    q.get(callback=_consume)


q = AsyncQueue()
sched.call_soon(lambda: producer(q, 10))
sched.call_soon(lambda: consumer(q))
sched.run()
