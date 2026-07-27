// pyG4Tet.cpp (FIXED v2 for Geant4 11.1.x)
// - Avoids calling G4Tet::CheckDegeneracy (non-static in this Geant4)
// - Provides a simple geometric degeneracy test based on tetra volume
//
// Place this file into: opengate_core/g4_bindings/pyG4Tet.cpp

#include <pybind11/pybind11.h>
#include <pybind11/stl.h>

#include <array>
#include <cmath>
#include <memory>
#include <stdexcept>

#include "G4Tet.hh"
#include "G4ThreeVector.hh"
#include "G4String.hh"

namespace py = pybind11;

// Simple degeneracy check: |6V| = | dot( (b-a), cross((c-a),(d-a)) ) |
static bool tet_is_degenerate(const G4ThreeVector &a,
                              const G4ThreeVector &b,
                              const G4ThreeVector &c,
                              const G4ThreeVector &d,
                              double eps = 1e-12) {
  const auto ab = b - a;
  const auto ac = c - a;
  const auto ad = d - a;
  const double sixV = ab.dot(ac.cross(ad));
  return std::abs(sixV) <= eps;
}

void init_G4Tet(py::module &m) {

  py::class_<G4Tet, std::unique_ptr<G4Tet>>(m, "G4Tet")
      // NOTE: Geant4 11.1.x constructor is:
      //   G4Tet(name, p1,p2,p3,p4, G4bool* degeneracyFlag = nullptr)
      .def(py::init([](const std::string &name,
                       const std::array<double, 3> &p1,
                       const std::array<double, 3> &p2,
                       const std::array<double, 3> &p3,
                       const std::array<double, 3> &p4) {
             G4bool deg = false;
             auto *t = new G4Tet(G4String(name.c_str()),
                                G4ThreeVector(p1[0], p1[1], p1[2]),
                                G4ThreeVector(p2[0], p2[1], p2[2]),
                                G4ThreeVector(p3[0], p3[1], p3[2]),
                                G4ThreeVector(p4[0], p4[1], p4[2]),
                                &deg);
             // If Geant4 says degenerate, delete and throw
             if (deg) {
               delete t;
               throw std::runtime_error("G4Tet: degenerate tetrahedron (Geant4 degeneracyFlag=true)");
             }
             return t;
           }),
           py::arg("name"), py::arg("p1"), py::arg("p2"), py::arg("p3"), py::arg("p4"))
      .def("GetCubicVolume", &G4Tet::GetCubicVolume)
      .def("Inside", &G4Tet::Inside);

  // Standalone helper: purely geometric degeneracy test
  m.def("tet_is_degenerate",
        [](const std::array<double, 3> &p1,
           const std::array<double, 3> &p2,
           const std::array<double, 3> &p3,
           const std::array<double, 3> &p4,
           double eps) {
          return tet_is_degenerate(G4ThreeVector(p1[0], p1[1], p1[2]),
                                   G4ThreeVector(p2[0], p2[1], p2[2]),
                                   G4ThreeVector(p3[0], p3[1], p3[2]),
                                   G4ThreeVector(p4[0], p4[1], p4[2]),
                                   eps);
        },
        py::arg("p1"), py::arg("p2"), py::arg("p3"), py::arg("p4"),
        py::arg("eps") = 1e-12);
}
