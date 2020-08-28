/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#include <pybind11/pybind11.h>
#include <pybind11/operators.h>

namespace py = pybind11;

// CLHEP::HepRotation
#include "G4RotationMatrix.hh"

void init_G4RotationMatrix(py::module &m) {

    py::class_<CLHEP::HepRep3x3>(m, "HepRep3x3")
        .def(py::init<>())
        .def(py::init<double, double, double,
            double, double, double,
            double, double, double>());

    py::class_<G4RotationMatrix>(m, "G4RotationMatrix")

        // constructors
        .def(py::init<>())
        .def(py::init<const G4RotationMatrix &>())

            // property
        .def("xx", &G4RotationMatrix::xx)
        .def("xy", &G4RotationMatrix::xy)
        .def("xz", &G4RotationMatrix::xz)
        .def("yx", &G4RotationMatrix::yx)
        .def("yy", &G4RotationMatrix::yy)
        .def("yz", &G4RotationMatrix::yz)
        .def("zx", &G4RotationMatrix::zx)
        .def("zy", &G4RotationMatrix::zy)
        .def("zz", &G4RotationMatrix::zz)
        .def_readonly_static("IDENTITY", &G4RotationMatrix::IDENTITY)

            // methods
        .def("colX", &G4RotationMatrix::colX)
        .def("colY", &G4RotationMatrix::colY)
        .def("colZ", &G4RotationMatrix::colZ)
        .def("rowX", &G4RotationMatrix::rowX)
        .def("rowY", &G4RotationMatrix::rowY)
        .def("rowZ", &G4RotationMatrix::rowZ)
        .def("getPhi", &G4RotationMatrix::getPhi)
        .def("getTheta", &G4RotationMatrix::getTheta)
        .def("getPsi", &G4RotationMatrix::getPsi)
        .def("phi", &G4RotationMatrix::phi)
        .def("theta", &G4RotationMatrix::theta)
        .def("psi", &G4RotationMatrix::psi)
        .def("getDelta", &G4RotationMatrix::getDelta)
        .def("getAxis", &G4RotationMatrix::getAxis)
        .def("delta", &G4RotationMatrix::axis)
        .def("axis", &G4RotationMatrix::delta)
        .def("phiX", &G4RotationMatrix::phiX)
        .def("phiY", &G4RotationMatrix::phiY)
        .def("phiZ", &G4RotationMatrix::phiZ)
        .def("thetaX", &G4RotationMatrix::thetaX)
        .def("thetaY", &G4RotationMatrix::thetaY)
        .def("thetaZ", &G4RotationMatrix::thetaZ)
        .def("setPhi", &G4RotationMatrix::setPhi)
        .def("setTheta", &G4RotationMatrix::setTheta)
        .def("setPsi", &G4RotationMatrix::setPsi)
        .def("setAxis", &G4RotationMatrix::setAxis)
        .def("setDelta", &G4RotationMatrix::setDelta)
        .def("isIdentity", &G4RotationMatrix::isIdentity)

        .def("rotateX", &G4RotationMatrix::rotateX, py::return_value_policy::reference)
        .def("rotateY", &G4RotationMatrix::rotateY, py::return_value_policy::reference)
        .def("rotateZ", &G4RotationMatrix::rotateZ, py::return_value_policy::reference)
            //.def("rotate",     &G4RotationMatrix::rotate, py::return_value_policy::reference)
            //.def("rotate",     f2_rotate, py::return_value_policy::reference)
        .def("rotateAxes", &G4RotationMatrix::rotateAxes, py::return_value_policy::reference)
        .def("inverse", &G4RotationMatrix::inverse)
        .def("invert", &G4RotationMatrix::invert, py::return_value_policy::reference)

        .def("rep3x3", &G4RotationMatrix::rep3x3)
        .def("set", [](G4RotationMatrix &r, const CLHEP::HepRep3x3 &mat) {
            r.set(mat);
        })

            // operators
            //.def(py::self_ns::str(py::self))
        .def(py::self == py::self)
        .def(py::self != py::self)
        .def(py::self > py::self)
        .def(py::self < py::self)
        .def(py::self >= py::self)
        .def(py::self <= py::self)
        .def(py::self * py::self)
        .def(py::self * G4ThreeVector())
        .def(py::self *= py::self);
}

