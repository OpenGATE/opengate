/* --------------------------------------------------
   Copyright (C): OpenGate Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#include "GateSPSAngDistribution.h"
#include "GateHelpers.h"

G4ThreeVector GateSPSAngDistribution::VGenerateOne() {
  // return GenerateOne();
  auto direction = GenerateOne();
  if (fDirectionRelativeToAttachedVolume) {
    direction = direction / direction.mag();
    direction = fGlobalRotation * direction;
  }
  return direction;
}
