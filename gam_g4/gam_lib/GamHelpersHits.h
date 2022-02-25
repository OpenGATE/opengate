/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#ifndef GAM_G4_GAMHELPERSHITS_H
#define GAM_G4_GAMHELPERSHITS_H

#include <pybind11/stl.h>
#include "G4TouchableHistory.hh"
#include "GamVHitAttribute.h"
#include "GamHitsCollection.h"

void CheckThatAttributeExists(const GamHitsCollection *hc, const std::string &name);

class GamHitsAttributesFiller {
public:
    GamHitsAttributesFiller(GamHitsCollection *input,
                            GamHitsCollection *output,
                            const std::set<std::string> &names);

    void Fill(size_t index);

    std::vector<GamVHitAttribute *> fInputHitAttributes;
    std::vector<GamVHitAttribute *> fOutputHitAttributes;
};

#endif // GAM_G4_GAMHELPERSHITS_H
