/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#include "GamParticleFilter.h"
#include "GamHelpersDict.h"

void GamParticleFilter::Initialize(py::dict &user_info) {
    fParticleName = DictStr(user_info, "particle");
}

bool GamParticleFilter::Accept(const G4Track *track) const {
    auto p = track->GetParticleDefinition()->GetParticleName();
    if (p == fParticleName) return true;
    return false;
}

bool GamParticleFilter::Accept(const G4Step *step) const {
    auto p = step->GetTrack()->GetParticleDefinition()->GetParticleName();
    if (p == fParticleName) return true;
    return false;
}