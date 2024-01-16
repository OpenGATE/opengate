/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#include <pybind11/pybind11.h>

namespace py = pybind11;

#include "G4ProcessTable.hh"
#include "G4ProcessVector.hh"
#include "G4RadioactiveDecay.hh"

void init_G4ProcessTable(py::module &m) {

  py::class_<G4ProcessTable, std::unique_ptr<G4ProcessTable, py::nodelete>>(
      m, "G4ProcessTable")
      .def("GetProcessTable", &G4ProcessTable::GetProcessTable,
           py::return_value_policy::reference)
      .def("Length", &G4ProcessTable::Length)
      .def(
          "FindProcesses",
          (G4ProcessVector * (G4ProcessTable::*)(const G4String &processName)) &
              G4ProcessTable::FindProcesses,
          py::return_value_policy::reference)
      .def(
          "FindRadioactiveDecay",
          [](G4ProcessTable &t) -> G4RadioactiveDecay * {
            std::cout << "here" << std::endl;
            {
              auto *pv = t.FindProcesses();
              for (auto i = 0; i < pv->size(); i++) {
                std::cout << (*pv)[i]->GetProcessName() << std::endl;
              }
            }

            auto *pv = t.FindProcesses("RadioactiveDecay");
            // auto *pv = t.FindProcesses("Decay");
            std::cout << pv << " size=" << pv->size() << std::endl;
            auto *p = (*pv)[0];
            std::cout << p << std::endl;
            return (G4RadioactiveDecay *)(p);
          },
          py::return_value_policy::reference);
}
