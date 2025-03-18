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
  if (!hc->IsDigiAttributeExists(name)) {
    std::ostringstream oss;
    oss << "The attribute '" << name << "' is required in the DigiCollection '"
        << hc->GetName() << "'. Abort";
    Fatal(oss.str());
  }
}

GateDigiAttributesFiller::GateDigiAttributesFiller(
    GateDigiCollection *input, GateDigiCollection *output,
    const std::set<std::string> &names) {
  for (const auto &att_name : names) {
    fInputDigiAttributes.push_back(input->GetDigiAttribute(att_name));
    fOutputDigiAttributes.push_back(output->GetDigiAttribute(att_name));
  }
}

void GateDigiAttributesFiller::Fill(size_t index) {
  for (size_t i = 0; i < fInputDigiAttributes.size(); i++) {
    fOutputDigiAttributes[i]->Fill(fInputDigiAttributes[i], index);
  }
}
