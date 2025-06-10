/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#ifndef GateSPSAngDistribution_h
#define GateSPSAngDistribution_h

#include "G4SPSAngDistribution.hh"

class GateSPSAngDistribution : public G4SPSAngDistribution {

public:
  // Cannot inherit from GenerateOne, so we consider VGenerateOne instead
  virtual G4ThreeVector VGenerateOne();

  // Store the global orientation that may be applied to the direction
  // in the GenerateOne function.
  // (Must be updated each run)
  bool fDirectionRelativeToAttachedVolume;
  G4ThreeVector fGlobalTranslation;
  G4RotationMatrix fGlobalRotation;
};

#endif // GateSPSAngDistribution_h
