/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#include "GateImageBox.h"
#include <G4Box.hh>
#include <pybind11/pybind11.h>
#include <pybind11/stl.h>

void init_GateImageBox(py::module &m) {

  py::class_<GateImageBox, G4Box>(m, "GateImageBox")
      .def(py::init<py::dict &>())
      .def("SetSlices", &GateImageBox::SetSlices)
#ifdef GATEIMAGEBOX_USE_OPENGL
      .def("InitialiseSlice", &GateImageBox::InitialiseSlice)
#endif
      ;
}
