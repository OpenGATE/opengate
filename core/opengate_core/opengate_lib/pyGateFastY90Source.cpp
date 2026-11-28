/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#include "GateFastY90Source.h"
#include <pybind11/pybind11.h>

void init_GateFastY90Source(py::module &m) {
  py::class_<GateFastY90Source, GateVoxelSource>(m, "GateFastY90Source")
      .def(py::init())
      .def("InitializeUserInfo", &GateFastY90Source::InitializeUserInfo);
}
