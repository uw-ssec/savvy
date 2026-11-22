"""In-process task queue: a thread pool reading from queue.Queue. Tasks are lost on restart."""
import queue
import threading

_tasks = queue.Queue()
_handlers = {}


def register(name):
    def deco(fn):
        _handlers[name] = fn
        return fn

    return deco


def enqueue(name, **kwargs):
    _tasks.put((name, kwargs))


def _worker():
    while True:
        name, kwargs = _tasks.get()
        try:
            _handlers[name](**kwargs)
        finally:
            _tasks.task_done()


def start(workers=4):
    for _ in range(workers):
        threading.Thread(target=_worker, daemon=True).start()
