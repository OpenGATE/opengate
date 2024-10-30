/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#include <pybind11/pybind11.h>

namespace py = pybind11;

#include "G4AssemblyVolume.hh"
#include "G4LogicalVolume.hh"

void init_G4AssemblyVolume(py::module &m) {

  py::class_<G4AssemblyVolume>(m, "G4AssemblyVolume")

      .def(py::init<>())
      .def("AddPlacedVolume",
           [](G4AssemblyVolume &a, G4LogicalVolume *pPlacedVolume,
              G4ThreeVector &translation, G4RotationMatrix *rotation) {
             a.AddPlacedVolume(pPlacedVolume, translation, rotation);
           })
      .def("MakeImprint", [](G4AssemblyVolume &a, G4LogicalVolume *pMotherLV,
                             G4ThreeVector &translationInMother,
                             G4RotationMatrix *pRotationInMother,
                             G4int copyNumBase, //= 0,
                             G4bool surfCheck   //= false
                          ) {
        a.MakeImprint(pMotherLV, translationInMother, pRotationInMother,
                      copyNumBase, surfCheck);
      });
}
