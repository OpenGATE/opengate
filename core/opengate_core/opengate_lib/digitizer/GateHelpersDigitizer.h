/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#ifndef OPENGATE_CORE_OPENGATEHELPERDIGITIZER_H
#define OPENGATE_CORE_OPENGATEHELPERDIGITIZER_H

#include "G4TouchableHistory.hh"
#include "GateDigiCollection.h"
#include "GateVDigiAttribute.h"
#include <pybind11/stl.h>

void CheckRequiredAttribute(const GateDigiCollection *hc,
                            const std::string &name);

class GateDigiAttributesFiller {
public:
  GateDigiAttributesFiller(GateDigiCollection *input,
                           GateDigiCollection *output,
                           const std::set<std::string> &names);

  void Fill(size_t index);

  std::vector<GateVDigiAttribute *> fInputDigiAttributes;
  std::vector<GateVDigiAttribute *> fOutputDigiAttributes;
};

#endif // OPENGATE_CORE_OPENGATEHELPERDIGITIZER_H
