/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#include <G4VUserTrackInformation.hh>

class GateUserTrackInformation : public G4VUserTrackInformation {
public:
  GateUserTrackInformation() = default;
  ~GateUserTrackInformation() override = default;

  int fInfoType;
};
