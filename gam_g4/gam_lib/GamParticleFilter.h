/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#ifndef GamParticleFilter_h
#define GamParticleFilter_h

#include <pybind11/stl.h>
#include "GamVFilter.h"

namespace py = pybind11;

class GamParticleFilter : public GamVFilter {

public:

    GamParticleFilter() : GamVFilter() {}

    virtual void Initialize(py::dict &user_info) override;

    virtual bool Accept(const G4Track *track) const override;

    virtual bool Accept(const G4Step *step) const override;

    G4String fParticleName;
};

#endif // GamParticleFilter_h
