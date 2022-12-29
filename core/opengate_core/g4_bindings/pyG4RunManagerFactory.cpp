/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */
#include <pybind11/pybind11.h>

namespace py = pybind11;

#include "G4RunManagerFactory.hh"
#include "G4MTRunManager.hh"

void init_G4RunManagerFactory(py::module &m) {

  py::class_<G4RunManagerFactory>(m, "G4RunManagerFactory")
    .def("CreateRunManager",
         []() -> G4RunManager * {
           auto *rm = G4RunManagerFactory::CreateRunManager(G4RunManagerType::Serial);
           std::cout << "G4RunManagerFactory " << rm->GetRunManagerType() << std::endl;
           std::cout << "G4RunManagerFactory " << rm->GetVersionString() << std::endl;
           return rm;
         }
    )
    .def("CreateMTRunManager",
         [](int nb_threads) -> G4RunManager * {
           //std::cout << nb_threads << std::endl;
           //auto *rm = G4RunManagerFactory::CreateRunManager(G4RunManagerType::MT, true, nb_threads);
           auto *rm = G4RunManagerFactory::CreateRunManager(G4RunManagerType::MT, true, nb_threads);
           //auto *rm = new G4MTRunManager();
           /*std::cout << "done CreateRunManager " << std::endl;
           std::cout << rm->GetRunManagerType() << std::endl;
           std::cout << rm->GetVersionString() << std::endl;*/
           return rm;
         }
    );
}
