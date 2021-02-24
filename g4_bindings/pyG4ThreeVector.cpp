/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */
#include <pybind11/pybind11.h>
#include <pybind11/operators.h>

namespace py = pybind11;

#include "G4ThreeVector.hh"

void init_G4ThreeVector(py::module &m) {
    py::class_<G4ThreeVector>(m, "G4ThreeVector")

        // constructor
        .def(py::init())
        .def(py::init<double>())
        .def(py::init<double, double>())
        .def(py::init<double, double, double>())
        .def(py::init<const G4ThreeVector &>())

            // properties
        .def_property("x", &G4ThreeVector::x, &G4ThreeVector::setX)
        .def_property("y", &G4ThreeVector::y, &G4ThreeVector::setY)
        .def_property("z", &G4ThreeVector::z, &G4ThreeVector::setZ)

            // stream output /// FIXME Not sure this is the right way to do
        .def("__repr__", [](const G4ThreeVector &a) {
            std::ostringstream os;
            os << a;
            return os.str();
        })
            // .def(py::self::str(py::self)) // <--- used with python-boost, not possible with pybind11

            // operator bracket. We add a control of the index
        .def("__getitem__", [](const G4ThreeVector &s, int i) {
            if (i >= 3)
                throw py::index_error();
            return s[i];
        })
        .def("__setitem__", [](G4ThreeVector &s, int i, float v) {
            if (i >= 3)
                throw py::index_error();
            s[i] = v;
        })

            // operator parenthesis ??? FIXME

            // operators
        .def(py::self == py::self)
        .def(py::self != py::self)
        .def(py::self += py::self)
            //.def(py::self -= py::self)  // warning: explicitly assigning value of variable of type 'const pybind11::detail::self_t' to itself [-Wself-assign-overloaded] // https://github.com/pybind/pybind11/issues/1893
        .def(py::self - py::self)
        .def(py::self + py::self)
        .def(py::self * py::self)   // this is the dot product
        .def(py::self * float())
        .def(py::self / float())
        .def(float() * py::self)
        .def(py::self *= float())
        .def(py::self /= float())
        .def(py::self > py::self)
        .def(py::self < py::self)
        .def(py::self >= py::self)
        .def(py::self <= py::self)

            // methods
        .def("set", &G4ThreeVector::set)
        .def("phi", &G4ThreeVector::phi)
        .def("mag", &G4ThreeVector::mag)
        .def("mag2", &G4ThreeVector::mag2)
        .def("setPhi", &G4ThreeVector::setPhi)
        .def("setTheta", &G4ThreeVector::setTheta)
        .def("setMag", &G4ThreeVector::setMag)
        .def("setPerp", &G4ThreeVector::setPerp)
        .def("setCylTheta", &G4ThreeVector::setCylTheta)
        .def("howNear", &G4ThreeVector::howNear)
        .def("deltaR", &G4ThreeVector::deltaR)
        .def("unit", &G4ThreeVector::unit)
        .def("orthogonal", &G4ThreeVector::orthogonal)
        .def("dot", &G4ThreeVector::dot)
        .def("cross", &G4ThreeVector::cross)
        .def("pseudoRapidity", &G4ThreeVector::pseudoRapidity)
        .def("setEta", &G4ThreeVector::setEta)
        .def("setCylEta", &G4ThreeVector::setCylEta)
        .def("setRThetaPhi", &G4ThreeVector::setRThetaPhi)
        .def("setREtaPhi", &G4ThreeVector::setREtaPhi)
        .def("setRhoPhiZ", &G4ThreeVector::setRhoPhiZ)
        .def("setRhoPhiEta", &G4ThreeVector::setRhoPhiEta)
        .def("getX", &G4ThreeVector::getX)
        .def("getY", &G4ThreeVector::getY)
        .def("getZ", &G4ThreeVector::getZ)
        .def("getR", &G4ThreeVector::getR)
        .def("getTheta", &G4ThreeVector::getTheta)
        .def("getPhi", &G4ThreeVector::getPhi)
        .def("r", &G4ThreeVector::r)
        .def("rho", &G4ThreeVector::rho)
        .def("getRho", &G4ThreeVector::getRho)
        .def("getEta", &G4ThreeVector::getEta)
        .def("setR", &G4ThreeVector::setR)
        .def("setRho", &G4ThreeVector::setRho)
        .def("compare", &G4ThreeVector::compare)
        .def("diff2", &G4ThreeVector::diff2)

            // static tolerance
        .def("getTolerance", &G4ThreeVector::getTolerance)

            // FIXME
            // .def("isParallel", &G4ThreeVector::isParallel, f_isParallel())
            // .def("isOrthogonal", &G4ThreeVector::isOrthogonal, f_isOrthogonal())

        .def("howParallel", &G4ThreeVector::howParallel)
        .def("howOrthogonal", &G4ThreeVector::howOrthogonal)
        .def("beta", &G4ThreeVector::beta)
        .def("gamma", &G4ThreeVector::gamma)
        .def("deltaPhi", &G4ThreeVector::deltaPhi)
        .def("coLinearRapidity", &G4ThreeVector::coLinearRapidity)

            // FIXME
            // with default param
        .def("isNear", &G4ThreeVector::isNear, py::arg("v"), py::arg("epsilon") = G4ThreeVector::getTolerance())
            // .def("isNear", [](const G4ThreeVector& v, const G4ThreeVector& w, double epsilon) {
            //                  return v.isNear(w,epsilon); })
            // .def("isNear", [](const G4ThreeVector& v, const G4ThreeVector& w) {
            //                  return v.isNear(w,v.getTolerance()); })

            // .def("theta", &G4ThreeVector::theta)
            // // .def("theta", f2_theta)
            // .def("cosTheta", f1_cosTheta)
            // //.def("cosTheta", f2_cosTheta)
            // .def("cos2Theta", f1_cos2Theta)
            // //.def("cos2Theta", f2_cos2Theta)
            // .def("perp2", f1_perp2)
            // //.def("perp2", f2_perp2)
            // .def("angle", f1_angle)
            // .def("angle", f2_angle)
            // .def("eta", f1_eta)
            // .def("eta", f2_eta)
            // .def("project", f1_project)
            // .def("project", f2_project)
            // .def("perpPart", f1_perpPart)
            // .def("perpPart", f2_perpPart)
            // .def("rapidity", f1_rapidity)
            // .def("rapidity", f2_rapidity)
            // .def("polarAngle",f1_polarAngle)
            // .def("polarAngle",f2_polarAngle)
            // .def("azimAngle", f1_azimAngle)
            // .def("azimAngle", f2_azimAngle)

            // static method (instance and static fields)
        .def_property("tolerance", &G4ThreeVector::getTolerance, &G4ThreeVector::setTolerance)

        .def("rotateX", &G4ThreeVector::rotateX)
        .def("rotateY", &G4ThreeVector::rotateY)
        .def("rotateZ", &G4ThreeVector::rotateZ)

        // .def("rotateUz", &G4ThreeVector::rotateUz,
        //      return_value_policy<reference_existing_object>())
        // .def("transform",&G4ThreeVector::transform,
        //      return_value_policy<reference_existing_object>())
        // .def("rotate", f1_rotate,
        //      return_value_policy<reference_existing_object>())
        // .def("rotate", f2_rotate,
        //      return_value_policy<reference_existing_object>())
        // .def("rotate", f5_rotate,
        //      return_value_policy<reference_existing_object>())

        ;
}
