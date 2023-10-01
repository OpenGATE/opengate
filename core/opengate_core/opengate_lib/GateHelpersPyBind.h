/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#ifndef GateHelpersPyBind_h
#define GateHelpersPyBind_h

#include <pybind11/stl.h>

namespace py = pybind11;

template <class T> T *PyBindGetVector(const py::array_t<T> &values) {
  py::buffer_info info = values.request();
  return static_cast<T *>(info.ptr);
}

#endif // GateHelpersPyBind_h
