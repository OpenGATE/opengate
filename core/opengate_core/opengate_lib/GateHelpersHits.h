/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#ifndef OPENGATE_CORE_OPENGATEHELPERSHITS_H
#define OPENGATE_CORE_OPENGATEHELPERSHITS_H

#include <pybind11/stl.h>
#include "G4TouchableHistory.hh"
#include "GateVHitAttribute.h"
#include "GateHitsCollection.h"

void CheckRequiredAttribute(const GateHitsCollection *hc, const std::string &name);

class GateHitsAttributesFiller {
public:
    GateHitsAttributesFiller(GateHitsCollection *input,
                            GateHitsCollection *output,
                            const std::set<std::string> &names);

    void Fill(size_t index);

    std::vector<GateVHitAttribute *> fInputHitAttributes;
    std::vector<GateVHitAttribute *> fOutputHitAttributes;
};

#endif // OPENGATE_CORE_OPENGATEHELPERSHITS_H
