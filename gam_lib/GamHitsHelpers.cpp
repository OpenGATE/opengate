/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#include "GamHitsHelpers.h"


// Check attribute
// CheckAttributeExists(fInputHitsCollection, "TotalEnergyDeposit")
//void CheckAttribute()

// NewHitsCollection(name, filename, att_names);

// fOutputHitsCollection->InitializeHitAttributes(fInputHitsCollection->GetHitsAttributeNames)

//
// HitsAttributesFiller f(fInputHitsCollection, fOutputHitsCollection, names)
// f->Fill(index);

GamHitsAttributesFiller::GamHitsAttributesFiller(GamHitsCollection *input,
                                                 GamHitsCollection *output,
                                                 const std::set<std::string> & names) {
    //fHitsAttributeNames = names;
    for (auto att_name: names) {
        DDD(att_name);
        fInputHitAttributes.push_back(input->GetHitAttribute(att_name));
        fOutputHitAttributes.push_back(output->GetHitAttribute(att_name));
    }
}

void GamHitsAttributesFiller::Fill(size_t index) {
    for (size_t i = 0; i < fInputHitAttributes.size(); i++) {
        fOutputHitAttributes[i]->Fill(fInputHitAttributes[i], index);
    }
}