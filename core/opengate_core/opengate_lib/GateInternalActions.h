/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#ifndef CORE_OPENGATE_LIB_GATEINTERNALACTIONS_H
#define CORE_OPENGATE_LIB_GATEINTERNALACTIONS_H

#include "GateVActor.h"

class GateInternalActions : public GateVActor {
public:
  using GateVActor::GateVActor;

  void NewStage() override;

public:
  void SetChemistryEnabled(bool f) { fChemistryEnabled = f; }
  [[nodiscard]] bool GetChemistryEnabled() const { return fChemistryEnabled; }

private:
  bool fChemistryEnabled = false;
};

#endif
