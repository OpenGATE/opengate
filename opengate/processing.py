import multiprocessing
import queue

from .exception import fatal


# define thin wrapper function to handle the queue
def target_func(q, f, *args, **kwargs):
    q.put(f(*args, **kwargs))


def dispatch_to_subprocess(func, *args, **kwargs):
    try:
        multiprocessing.set_start_method("spawn")
    except RuntimeError:
        pass

    q = multiprocessing.Manager().Queue()
    # FIXME: would this also work?
    # q = multiprocessing.Queue()
    p = multiprocessing.Process(
        target=target_func, args=(q, func, *args), kwargs=kwargs
    )
    p.start()
    p.join()  # (timeout=10)  # timeout might be needed

    try:
        return q.get(block=False)
    except queue.Empty:
        fatal("The queue is empty. The spawned process probably died.")
