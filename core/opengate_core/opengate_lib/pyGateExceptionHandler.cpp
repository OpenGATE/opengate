/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#include <pybind11/pybind11.h>
#include <pybind11/stl.h>
#include "GateExceptionHandler.h"

namespace py = pybind11;

class PyGateExceptionHandler : public GateExceptionHandler {
public:
    // Inherit the constructors
    using GateExceptionHandler::GateExceptionHandler;

    G4bool Notify(const char *originOfException,
                  const char *exceptionCode,
                  G4ExceptionSeverity severity,
                  const char *description) override {
        PYBIND11_OVERLOAD(G4bool, GateExceptionHandler, Notify,
                          originOfException,
                          exceptionCode,
                          severity,
                          description
        );
    }
};


void init_GateExceptionHandler(py::module &m) {

    py::enum_<G4ExceptionSeverity>(m, "G4ExceptionSeverity")
            .value("FatalException", FatalException)
            .value("FatalErrorInArgument", FatalErrorInArgument)
            .value("RunMustBeAborted", RunMustBeAborted)
            .value("EventMustBeAborted", EventMustBeAborted)
            .value("JustWarning", JustWarning)
            .export_values();

    py::class_<GateExceptionHandler, PyGateExceptionHandler>(m, "GateExceptionHandler")
            .def(py::init())
            .def("Notify", &GateExceptionHandler::Notify);
}


