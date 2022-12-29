from opengate import log
import time
import random
import sys
from .ExceptionHandler import *
from multiprocessing import Process, set_start_method, Queue
import os


class EngineBase:
    """
    FIXME
    """

    def __init__(self):
        # debug verbose
        self.verbose_destructor = False

    def __del__(self):
        if self.verbose_destructor:
            print("del EngineBase")
