/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#include <pybind11/pybind11.h>

#include "GateCopyNumberFilter.h"

namespace py = pybind11;

void init_GateCopyNumberFilter(py::module &m) {
  // Expose the C++ filter used by the Python CopyNumberFilter wrapper in
  // opengate/actors/filters.py.
  py::class_<GateCopyNumberFilter, GateVFilter>(m, "GateCopyNumberFilter")
      .def(py::init<>())
      .def("InitializeUserInfo", &GateCopyNumberFilter::InitializeUserInfo);
}
