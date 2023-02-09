/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */
#include <pybind11/pybind11.h>

namespace py = pybind11;

#include "G4VProcess.hh"
#include <streambuf>

// // https://pybind11.readthedocs.io/en/stable/advanced/classes.html
// // Needed helper class because of the pure virtual method
// class PyG4VProcess : public G4VProcess {
// public:
//   // Inherit the constructors
//   using G4VProcess::G4VProcess;
//   // Trampoline (need one for each virtual function)
//   G4int GetCopyNo() const override {
//     PYBIND11_OVERLOAD_PURE(G4int, G4VProcess, GetCopyNo, );
//   }
// };

void init_G4VProcess(py::module &m) {

  py::class_<G4VProcess, std::unique_ptr<G4VProcess, py::nodelete>>(
      m, "G4VProcess");
  //.def(py::init<const G4String & >());
}
