#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import pickle


# Example to illustrate the impact of handling self.__dict__
# in the __getstate__ method


class Toto:
    def __init__(self, a, b):
        self.a = a
        self.b = b

    def __getstate__(self):
        self.a = None
        return self.__dict__

    def __str__(self) -> str:
        s = f"a = {self.a}\n"
        s += f"b = {self.b}\n"
        return s


class Pippo:
    def __init__(self, a, b):
        self.a = a
        self.b = b

    def __getstate__(self):
        d = dict(
            self.__dict__
        )  # need to call dict() to created new instance, not only a reference
        d["a"] = None
        return d

    def __str__(self) -> str:
        s = f"a = {self.a}\n"
        s += f"b = {self.b}\n"
        return s


t = Toto("a", "b")

print("** Object t **")
print("Original object before pickling:")
print(t)
pickled_t = pickle.dumps(t)
print("Original object after pickling:")
print(t)
reloaded_t = pickle.loads(pickled_t)
print("Reloaded object:")
print(reloaded_t)


p = Pippo("a", "b")

print("** Object p **")
print("Original object before pickling:")
print(p)
pickled_p = pickle.dumps(p)
print("Original object after pickling:")
print(p)
reloaded_p = pickle.loads(pickled_p)
print("Reloaded object:")
print(reloaded_p)
