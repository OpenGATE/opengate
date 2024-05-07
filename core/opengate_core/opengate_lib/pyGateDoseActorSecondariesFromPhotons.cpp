/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#include <pybind11/pybind11.h>
#include <pybind11/stl.h>

namespace py = pybind11;

#include "GateDoseActorSecondariesFromPhotons.h"

void init_GateDoseActorSecondariesFromPhotons(py::module &m) {
  py::class_<GateDoseActorSecondariesFromPhotons,
             std::unique_ptr<GateDoseActorSecondariesFromPhotons, py::nodelete>,
             GateVActor>(m, "GateDoseActorSecondariesFromPhotons")
      .def(py::init<py::dict &>())
      .def_readwrite("NbOfEvent",
                     &GateDoseActorSecondariesFromPhotons::NbOfEvent)
      .def_readwrite("cpp_edep_image",
                     &GateDoseActorSecondariesFromPhotons::cpp_edep_image)
      .def_readwrite("cpp_square_image",
                     &GateDoseActorSecondariesFromPhotons::cpp_square_image)
      .def_readwrite("fPhysicalVolumeName",
                     &GateDoseActorSecondariesFromPhotons::fPhysicalVolumeName);
}
