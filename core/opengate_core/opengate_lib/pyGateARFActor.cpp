/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#include <pybind11/functional.h>
#include <pybind11/pybind11.h>
#include <pybind11/stl.h>

namespace py = pybind11;

#include "GateARFActor.h"

void init_GateARFActor(py::module &m) {
  py::class_<GateARFActor, std::unique_ptr<GateARFActor, py::nodelete>,
             GateVActor>(m, "GateARFActor")
      .def(py::init<py::dict &>())
      .def("SetARFFunction",
           &GateARFActor::SetARFFunction) // FIXME, unsure what to do, seg fault
                                          // after dest
      .def_readonly("fCurrentNumberOfHits", &GateARFActor::fCurrentNumberOfHits)
      .def_readonly("fEnergy", &GateARFActor::fEnergy)
      .def_readonly("fPositionX", &GateARFActor::fPositionX)
      .def_readonly("fPositionY", &GateARFActor::fPositionY)
      .def_readonly("fDirectionX", &GateARFActor::fDirectionX)
      .def_readonly("fDirectionY", &GateARFActor::fDirectionY);
}
