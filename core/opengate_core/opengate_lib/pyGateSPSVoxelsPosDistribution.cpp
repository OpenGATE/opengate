/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#include "GateSPSPosDistribution.h"
#include "GateSPSVoxelsPosDistribution.h"
#include <pybind11/pybind11.h>
#include <pybind11/stl.h>

namespace py = pybind11;

void init_GateSPSVoxelsPosDistribution(py::module &m) {

  py::class_<GateSPSVoxelsPosDistribution, GateSPSPosDistribution>(
      m, "GateSPSVoxelsPosDistribution")
      .def(py::init())
      // The setter copies all three CDFs (std::vector), which for a
      // multi-million-voxel image takes seconds. Geant4 worker threads call it
      // during their initialisation; without releasing the GIL those copies are
      // serialised and block the Python physics constructor
      // (UserLimitsPhysics) running on the same threads, which makes
      // G4MTRunManager::Initialize() appear to hang. The copy touches no Python
      // API, so the GIL can be released for its whole duration. See #1163.
      .def("SetCumulativeDistributionFunction",
           &GateSPSVoxelsPosDistribution::SetCumulativeDistributionFunction,
           py::call_guard<py::gil_scoped_release>())
      .def("VGenerateOne", &GateSPSVoxelsPosDistribution::VGenerateOne)
      .def_readwrite("cpp_edep_image",
                     &GateSPSVoxelsPosDistribution::cpp_image);
}
