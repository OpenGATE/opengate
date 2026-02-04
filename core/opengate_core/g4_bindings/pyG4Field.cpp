/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#include <pybind11/pybind11.h>

namespace py = pybind11;

#include "G4Field.hh"

void init_G4Field(py::module &m) {
  py::class_<G4Field, std::unique_ptr<G4Field, py::nodelete>>(
      m, "G4Field")

    .def(py::init<G4bool>())
    .def(py::init<const G4Field &>())


    .def("GetFieldValue", &G4Field::GetFieldValue);

    .def("DoesFieldChangeEnergy", &G4Field::DoesFieldChangeEnergy);

    .def("IsGravityActive", &G4Field::IsGravityActive);
    .def("SetGravityActive", &G4Field::SetGravityActive);

}
