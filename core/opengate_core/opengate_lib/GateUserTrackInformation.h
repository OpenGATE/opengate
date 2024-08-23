/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#ifndef GateUserTrackInformation_h
#define GateUserTrackInformation_h

#include "G4VUserTrackInformation.hh"
#include "GateVActor.h"
#include <map>

class GateUserTrackInformation : public G4VUserTrackInformation {

public:
  GateUserTrackInformation();

  ~GateUserTrackInformation() override = default;

  void Print() const override;

  int GetScatterOrder() const;

  void Apply(const G4Step *step);

protected:
  int fScatterOrder;
};

#endif // GateUserTrackInformation_h
