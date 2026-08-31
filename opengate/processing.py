import multiprocessing
import queue
from .exception import fatal
import os
import sys


# define a thin wrapper function to handle the queue
def target_func(q, f, *args, **kwargs):
    q.put(f(*args, **kwargs))


def dispatch_to_subprocess(func, *args, **kwargs):
    # 1. Determine the start method
    # macOS ('darwin') and Windows ('nt') MUST use spawn for GUI safety
    # otherwise, it crashs with qt visualization
    if sys.platform == "darwin" or os.name == "nt":
        method_name = "spawn"
    else:
        # Linux can usually handle fork, which is faster.
        # However, if using Qt on Linux, 'spawn' might eventually be safer there too.
        method_name = "fork"

    # 2. Set the method
    # strictly speaking, set_start_method should only be called once.
    # checking get_start_method() is safer than try/except
    current_method = multiprocessing.get_start_method(allow_none=True)
    if current_method != method_name and current_method is not None:
        # If it is already set to something else, we can't change it.
        # This acts as a warning, or you can force a Context (advanced)
        pass
    elif current_method is None:
        try:
            multiprocessing.set_start_method(method_name)
        except RuntimeError:
            pass

    # 3. Select the Queue type based on the method
    # If we are spawning, standard Queue is supposed to be safe and faster.
    # if method_name == "spawn":
    #    q = multiprocessing.Queue()
    # else:
    # If forking, Manager is safer to avoid lock deadlocks
    # However=> we observe random crashs. So we switch to standard, safer, slower Manager.Queue
    q = multiprocessing.Manager().Queue()

    # 4. Create and start the process
    p = multiprocessing.Process(
        target=target_func, args=(q, func, *args), kwargs=kwargs
    )
    p.start()
    p.join()

    # 5. Retrieve result
    try:
        # We can usually block=True here because p.join() has finished,
        # but if the child crashed without putting data, block=False catches it.
        return q.get(block=False)
    except queue.Empty:
        fatal("The queue is empty. The spawned process probably died or crashed.")
        return None
