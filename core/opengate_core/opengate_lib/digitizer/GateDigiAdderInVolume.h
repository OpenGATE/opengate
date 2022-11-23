/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#ifndef GateHitAdderInVolume_h
#define GateHitAdderInVolume_h

#include "GateDigitizerAdderActor.h"

/*
    Helper class used by GateDigitizerAdderActor
 */

class GateDigiAdderInVolume {
public:
  GateDigiAdderInVolume();

  double fFinalEdep = 0;
  double fMaxEdep = 0;
  double fFinalTime = MAXFLOAT;
  G4ThreeVector fFinalPosition;
  size_t fFinalIndex = 0;

  void Update(GateDigitizerAdderActor::AdderPolicy fPolicy, size_t i,
              double edep, const G4ThreeVector &pos, double time);

  void Terminate(GateDigitizerAdderActor::AdderPolicy fPolicy);
};

#endif // GateHitAdderInVolume_h
