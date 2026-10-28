/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#include "GateMagneticField.h"
#include <G4LogicalVolume.hh>
#include <G4MagneticField.hh>
#include <pybind11/pybind11.h>
#include <pybind11/stl.h>

namespace py = pybind11;

// python bindings for GateMagneticField
void init_GateMagneticField(py::module &m) {

  py::class_<GateMagneticField, G4MagneticField,
             std::unique_ptr<GateMagneticField, py::nodelete>>(
      m, "GateMagneticField")

      .def(py::init([](G4MagneticField *inner,
                       const G4LogicalVolume *logical_volume) {
             return new GateMagneticField(inner, logical_volume);
           }),
           py::arg("inner_field"), py::arg("logical_volume"));
}
