import heapq
import time
from collections import deque
from select import select


class Scheduler:
    def __init__(self):
        self.ready = deque()
        self.sleeping = []
        self.sequence = 0
        self.clock = time.time
        self._read_waiting = {}
        self._write_waiting = {}

    def call_soon(self, func):
        self.ready.append(func)

    def call_later(self, delay, func):
        self.sequence += 1
        deadline = time.time() + delay
        heapq.heappush(self.sleeping, (deadline, self.sequence, func))

    def read_wait(self, fileno, func):
        # Trigger func() when fileno is readable
        self._read_waiting[fileno] = func

    def write_wait(self, fileno, func):
        # Trigger func() when fileno is writeable
        self._write_waiting[fileno] = func

    def run(self):
        while self.ready or self.sleeping or self._read_waiting or self._write_waiting:
            if not self.ready:
                if self.sleeping:
                    deadline, _, func = self.sleeping[0]
                    timeout = deadline - time.time()
                    timeout = max(timeout, 0)
                else:
                    timeout = None
                # Wait for I/O (and sleep)
                can_read, can_write, _ = select(
                    self._read_waiting, self._write_waiting, [], timeout
                )

                for fd in can_read:
                    self.ready.append(self._read_waiting.pop(fd))
                for fd in can_write:
                    self.ready.append(self._write_waiting.pop(fd))

                # Check for sleeping tasks
                now = time.time()
                while self.sleeping:
                    if now > self.sleeping[0][0]:
                        self.ready.append(heapq.heappop(self.sleeping)[2])
                    else:
                        break

            while self.ready:
                func = self.ready.popleft()
                func()

    def new_task(self, coro):
        self.ready.append(Task(coro))

    async def sleep(self, delay):
        self.call_later(delay, self.current)
        self.current = None
        await switch()

    async def recv(self, sock, maxbytes):
        self.read_wait(sock, self.current)
        self.current = None
        await switch()
        return sock.recv(maxbytes)

    async def send(self, sock, data):
        self.write_wait(sock, self.current)
        self.current = None
        await switch()
        return sock.send(data)

    async def accept(self, sock):
        self.read_wait(sock, self.current)
        self.current = None
        await switch()
        return sock.accept()


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
# sched.new_task(producer(q, 10))
# sched.new_task(consumer(q))


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

from socket import *


async def tcp_server(addr):
    sock = socket(AF_INET, SOCK_STREAM)
    sock.bind(addr)
    sock.listen(1)
    while True:
        client, addr = await sched.accept(sock)
        sched.new_task(echo_handler(client))


async def echo_handler(sock):
    while True:
        data = await sched.recv(sock, 10240)
        if not data:
            break
        await sched.send(sock, b"Got: " + data)
    print("Connection closed")
    sock.close()


sched.new_task(tcp_server(("", 30000)))

sched.run()
