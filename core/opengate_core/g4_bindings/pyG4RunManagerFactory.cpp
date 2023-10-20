/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */
#include <pybind11/pybind11.h>
#include <pybind11/stl.h>

namespace py = pybind11;

#include "G4MTRunManager.hh"
#include "G4RunManagerFactory.hh"

void init_G4RunManagerFactory(py::module &m) {

  py::class_<G4RunManagerFactory>(m, "G4RunManagerFactory")
      .def("CreateSerialRunManager",
           []() -> G4RunManager * {
             auto *rm = G4RunManagerFactory::CreateRunManager(
                 G4RunManagerType::Serial);
             return rm;
           })
      .def("CreateMTRunManager",
           [](int nb_threads) -> G4RunManager * {
             auto *rm = G4RunManagerFactory::CreateRunManager(
                 G4RunManagerType::MT, true, nb_threads);
             return rm;
           })
      .def("GetOptions", &G4RunManagerFactory::GetOptions);
}
