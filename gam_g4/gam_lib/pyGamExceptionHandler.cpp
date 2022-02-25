/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#include <pybind11/pybind11.h>
#include <pybind11/stl.h>
#include "GamExceptionHandler.h"

namespace py = pybind11;

class PyGamExceptionHandler : public GamExceptionHandler {
public:
    // Inherit the constructors
    using GamExceptionHandler::GamExceptionHandler;

    G4bool Notify(const char *originOfException,
                  const char *exceptionCode,
                  G4ExceptionSeverity severity,
                  const char *description) override {
        PYBIND11_OVERLOAD(G4bool, GamExceptionHandler, Notify,
                          originOfException,
                          exceptionCode,
                          severity,
                          description
        );
    }
};


void init_GamExceptionHandler(py::module &m) {

    py::enum_<G4ExceptionSeverity>(m, "G4ExceptionSeverity")
            .value("FatalException", FatalException)
            .value("FatalErrorInArgument", FatalErrorInArgument)
            .value("RunMustBeAborted", RunMustBeAborted)
            .value("EventMustBeAborted", EventMustBeAborted)
            .value("JustWarning", JustWarning)
            .export_values();

    py::class_<GamExceptionHandler, PyGamExceptionHandler>(m, "GamExceptionHandler")
            .def(py::init())
            .def("Notify", &GamExceptionHandler::Notify);
}


