/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#ifndef GatePositroniumDecayModelParams_h
#define GatePositroniumDecayModelParams_h

#include <vector>

enum PositroniumDecayKind {k2Gamma, k3Gamma};

enum PositronElectronInteraction {kParaPs, kDirect, kOrthoPs};

struct PositroniumDecayModelParams
{
  std::vector<double> fFractions;
  std::vector<double> fLifetimes;
  std::vector<double> fPromptGammaProbabilities;
  std::vector<double> fPromptGammaEnergy;
  std::vector<PositroniumDecayKind> fDecayKind;
  std::vector<PositronElectronInteraction> fPositronInteractions;
};

#endif
