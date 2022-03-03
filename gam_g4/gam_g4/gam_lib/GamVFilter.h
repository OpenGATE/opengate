/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#ifndef GamVFilter_h
#define GamVFilter_h

#include <pybind11/stl.h>
#include "G4Event.hh"
#include "G4Run.hh"
#include "G4Step.hh"

namespace py = pybind11;

class GamVFilter {

public:

    GamVFilter();

    virtual ~GamVFilter();

    virtual void Initialize(py::dict &user_info);

    virtual bool Accept(const G4Run *run) const;

    virtual bool Accept(const G4Event *event) const;

    virtual bool Accept(const G4Track *track) const;

    virtual bool Accept(const G4Step *step) const;

};

#endif // GamVFilter_h
