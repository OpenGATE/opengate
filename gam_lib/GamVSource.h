/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#ifndef GamVSource_h
#define GamVSource_h

#include "GamHelpers.h"
#include "G4VPrimitiveScorer.hh"
#include "G4Event.hh"
#include "G4Run.hh"
#include <pybind11/stl.h>

namespace py = pybind11;

class GamVSource {

public:

    GamVSource() {}
    virtual ~GamVSource() {}

    // Called at initialisation
    virtual void initialize(py::dict & /*user_info*/) {}

    virtual double PrepareNextTime(double current_simulation_time) {
        Fatal("PrepareNextTime must be overloaded");
        return current_simulation_time;
    }

    virtual void GeneratePrimaries(G4Event * /*event*/, double /*time*/) {
        Fatal("GeneratePrimaries must be overloaded");
    }

};

#endif // GamVSource_h
