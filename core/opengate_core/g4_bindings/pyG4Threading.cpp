/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */
#include <pybind11/pybind11.h>

namespace py = pybind11;

#include <G4Threading.hh>

void init_G4Threading(py::module &m) {

  m.def("G4GetThreadId", &G4Threading::G4GetThreadId);
  m.def("IsMultithreadedApplication", &G4Threading::IsMultithreadedApplication);
  m.def("IsMasterThread", &G4Threading::IsMasterThread);
  m.def("IsWorkerThread", &G4Threading::IsWorkerThread);
  m.def("GetNumberOfRunningWorkerThreads",
        &G4Threading::GetNumberOfRunningWorkerThreads);
}
