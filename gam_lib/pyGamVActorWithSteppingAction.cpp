/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#include <pybind11/pybind11.h>
#include <pybind11/stl.h>
#include <pybind11/stl_bind.h>

#include "G4Step.hh"
#include "G4TouchableHistory.hh"

namespace py = pybind11;

#include "GamVActorWithSteppingAction.h"

class PyGamVActorWithSteppingAction : public GamVActorWithSteppingAction {
public:
    /* Inherit the constructors */
    using GamVActorWithSteppingAction::GamVActorWithSteppingAction;

    void SteppingAction(G4Step *step, G4TouchableHistory *touchable) override {
        PYBIND11_OVERLOAD(void,
                          GamVActorWithSteppingAction,
                          SteppingAction,
                          step,
                          touchable
        );
    }

};

void init_GamVActorWithSteppingAction(py::module &m) {
    py::class_<GamVActorWithSteppingAction, PyGamVActorWithSteppingAction, GamVActor>(m, "GamVActorWithSteppingAction")
        .def(py::init<std::string>())
        .def("SteppingAction", &GamVActorWithSteppingAction::SteppingAction);
}

