/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#include "GateHelpersDigitizer.h"

// Check attribute
void CheckRequiredAttribute(const GateDigiCollection *hc,
                            const std::string &name) {
  if (not hc->IsDigiAttributeExists(name)) {
    std::ostringstream oss;
    oss << "The attribute '" << name << "' is required in the HitsCollection '"
        << hc->GetName() << "'. Abort";
    Fatal(oss.str());
  }
}

GateHitsAttributesFiller::GateHitsAttributesFiller(
    GateDigiCollection *input, GateDigiCollection *output,
    const std::set<std::string> &names) {
  for (const auto &att_name : names) {
    fInputHitAttributes.push_back(input->GetDigiAttribute(att_name));
    fOutputHitAttributes.push_back(output->GetDigiAttribute(att_name));
  }
}

void GateHitsAttributesFiller::Fill(size_t index) {
  for (size_t i = 0; i < fInputHitAttributes.size(); i++) {
    fOutputHitAttributes[i]->Fill(fInputHitAttributes[i], index);
  }
}
