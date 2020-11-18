/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#ifndef GamVSource_h
#define GamVSource_h

#include <pybind11/stl.h>
#include "G4Event.hh"
#include "GamHelpers.h"

namespace py = pybind11;

class GamVSource {

public:

    virtual ~GamVSource() {}

    // Called at initialisation
    virtual void initialize(py::dict &user_info) {
        name = py::str(user_info["name"]);
        start_time = py::float_(user_info["start_time"]);
        end_time = py::float_(user_info["end_time"]);
    }

    virtual void PrepareNextRun() {
        m_events_per_run.push_back(0);
    }

    virtual double PrepareNextTime(double current_simulation_time) {
        Fatal("PrepareNextTime must be overloaded");
        return current_simulation_time;
    }

    virtual void GeneratePrimaries(G4Event * /*event*/, double /*time*/) {
        m_events_per_run.back()++;
        //Fatal("GeneratePrimaries must be overloaded");
    }

    std::vector<int> m_events_per_run;
    std::string name;
    double start_time;
    double end_time;
};

#endif // GamVSource_h
