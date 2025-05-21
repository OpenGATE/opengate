import multiprocessing
import queue
from .exception import fatal
import os


# define a thin wrapper function to handle the queue
def target_func(q, f, *args, **kwargs):
    q.put(f(*args, **kwargs))


def dispatch_to_subprocess(func, *args, **kwargs):
    if os.name == "nt":
        # Windows: 'spawn' is required
        start_method = "spawn"
    else:
        # Unix (Linux or macOS)
        # On Unix, 'fork' is faster than 'spawn' but require Manager().Queue()
        start_method = "fork"
    try:
        multiprocessing.set_start_method(start_method)
    except RuntimeError:
        pass

    # Queue is faster than Manager().Queue() but fails with fork
    # q = multiprocessing.Queue()
    q = multiprocessing.Manager().Queue()
    p = multiprocessing.Process(
        target=target_func, args=(q, func, *args), kwargs=kwargs
    )
    p.start()
    p.join()

    try:
        return q.get(block=False)
    except queue.Empty:
        fatal("The queue is empty. The spawned process probably died.")
        return None
