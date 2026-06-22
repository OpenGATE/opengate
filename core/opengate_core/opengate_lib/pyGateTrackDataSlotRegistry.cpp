/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#include "GateTrackDataSlotRegistry.h"
#include <pybind11/pybind11.h>

namespace py = pybind11;

void init_GateTrackDataSlotRegistry(py::module &m) {
  py::class_<GateTrackDataSlotRegistry>(m, "GateTrackDataSlotRegistry")
      .def_static("Clear", &GateTrackDataSlotRegistry::Clear);
}
