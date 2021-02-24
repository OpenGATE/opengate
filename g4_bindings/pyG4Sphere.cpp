/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#include <pybind11/pybind11.h>

namespace py = pybind11;

#include "G4Sphere.hh"

void init_G4Sphere(py::module &m) {
    py::class_<G4Sphere, G4VSolid>(m, "G4Sphere")

        .def(py::init<const G4String &, G4double, G4double,
            G4double, G4double, G4double, G4double>())

            // the following are not really needed
        .def("GetInnerRadius", &G4Sphere::GetInnerRadius)
        .def("GetOuterRadius", &G4Sphere::GetOuterRadius)
        .def("GetStartPhiAngle", &G4Sphere::GetStartPhiAngle)
        .def("GetDeltaPhiAngle", &G4Sphere::GetDeltaPhiAngle)
        .def("GetStartThetaAngle()", &G4Sphere::GetStartThetaAngle)
        .def("GetDeltaThetaAngle()", &G4Sphere::GetDeltaThetaAngle)
        .def("GetSinStartPhi", &G4Sphere::GetSinStartPhi)
        .def("GetCosStartPhi", &G4Sphere::GetCosStartPhi)
        .def("GetSinEndPhi  ", &G4Sphere::GetSinEndPhi)
        .def("GetCosEndPhi  ", &G4Sphere::GetCosEndPhi)
        .def("GetSinStartTheta", &G4Sphere::GetSinStartTheta)
        .def("GetCosStartTheta", &G4Sphere::GetCosStartTheta)
        .def("GetSinEndTheta", &G4Sphere::GetSinEndTheta)
        .def("GetCosEndTheta", &G4Sphere::GetCosEndTheta);

    // operators
    //.def(self_ns::str(self))
}
