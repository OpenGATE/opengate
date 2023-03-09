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

  GateDigiAdderInVolume(GateDigitizerAdderActor::AdderPolicy policy,
                        bool timeDifferenceFlag, bool numberOfHitsFlag);

  GateDigitizerAdderActor::AdderPolicy fPolicy;
  bool fTimeDifferenceFlag;
  bool fNumberOfHitsFlag;

  double fFinalEdep = 0;
  double fMaxEdep = 0;
  double fFinalTime = MAXFLOAT;
  G4ThreeVector fFinalPosition;
  size_t fFinalIndex = 0;
  int fNumberOfHits;

  double fEarliestTime = MAXFLOAT;
  double fLatestTime = 0;
  double fDifferenceTime = 0;

  void Update(size_t i, double edep, const G4ThreeVector &pos, double time);

  void Terminate();
};

#endif // GateHitAdderInVolume_h
