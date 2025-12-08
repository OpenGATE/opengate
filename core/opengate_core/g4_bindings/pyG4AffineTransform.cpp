/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#include <pybind11/pybind11.h>

namespace py = pybind11;

#include "G4AffineTransform.hh"

void init_G4AffineTransform(py::module &m) {
  py::class_<G4AffineTransform>(m, "G4AffineTransform")
      .def(py::init())
      .def("Product", &G4AffineTransform::Product)
      .def("InverseProduct", &G4AffineTransform::InverseProduct)
      .def("TransformPoint", &G4AffineTransform::TransformPoint)
      .def("InverseTransformPoint", &G4AffineTransform::InverseTransformPoint)
      .def("TransformAxis", &G4AffineTransform::TransformAxis)
      .def("InverseTransformAxis", &G4AffineTransform::InverseTransformAxis)
      .def("ApplyPointTransform", &G4AffineTransform::ApplyPointTransform)
      .def("ApplyAxisTransform", &G4AffineTransform::ApplyAxisTransform)
      .def("NetRotation", &G4AffineTransform::NetRotation)
      .def("NetTranslation", &G4AffineTransform::NetTranslation)
      .def("InverseNetRotation", &G4AffineTransform::InverseNetRotation)
      .def("InverseNetTranslation", &G4AffineTransform::InverseNetTranslation)
      .def("Inverse", &G4AffineTransform::Inverse)
      .def("Invert", &G4AffineTransform::Invert);
}
