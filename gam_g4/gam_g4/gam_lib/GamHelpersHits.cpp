/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#include "GamHelpersHits.h"

// Check attribute
void CheckThatAttributeExists(const GamHitsCollection *hc, const std::string &name) {
    if (not hc->IsHitAttributeExists(name)) {
        std::ostringstream oss;
        oss << "The attribute '" << name << "' is required but not on the HitsCollection '"
            << hc->GetName() << "'. Abort";
        Fatal(oss.str());
    }
}

GamHitsAttributesFiller::GamHitsAttributesFiller(GamHitsCollection *input,
                                                 GamHitsCollection *output,
                                                 const std::set<std::string> &names) {
    for (auto att_name: names) {
        fInputHitAttributes.push_back(input->GetHitAttribute(att_name));
        fOutputHitAttributes.push_back(output->GetHitAttribute(att_name));
    }
}

void GamHitsAttributesFiller::Fill(size_t index) {
    for (size_t i = 0; i < fInputHitAttributes.size(); i++) {
        fOutputHitAttributes[i]->Fill(fInputHitAttributes[i], index);
    }
}