/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#include <pybind11/pybind11.h>
#include <pybind11/stl.h>

namespace py = pybind11;

#include "G4IInterpolator.hh"
#include "G4PixeShellDataSet.hh"

void init_G4PixeShellDataSet(py::module &m) {
  py::class_<G4PixeShellDataSet,
             std::unique_ptr<G4PixeShellDataSet, py::nodelete>>(
      m, "G4PixeShellDataSet")
      .def(py::init<G4int, G4IInterpolator *, const G4String &,
                    const G4String &, const G4String &, G4double, G4double>())
      .def("LoadData", &G4PixeShellDataSet::LoadData)
      .def("NumberOfComponents", &G4PixeShellDataSet::NumberOfComponents)
      .def("GetEnergies",
           [](G4PixeShellDataSet &d, G4int componentId) {
             std::vector<double> e = d.GetEnergies(componentId);
             return e;
           })
      .def("GetData",
           [](G4PixeShellDataSet &d, G4int componentId) {
             std::vector<double> e = d.GetData(componentId);
             return e;
           })
      .def("GetData", &G4PixeShellDataSet::GetData)
      .def("PrintData", &G4PixeShellDataSet::PrintData);
}
