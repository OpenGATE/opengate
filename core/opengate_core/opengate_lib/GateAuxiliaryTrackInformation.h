/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#ifndef GateAuxiliaryTrackInformation_h
#define GateAuxiliaryTrackInformation_h

#include "G4VAuxiliaryTrackInformation.hh"

class GateIntegerCounterAuxiliaryTrackInformation
    : public G4VAuxiliaryTrackInformation {
public:
  GateIntegerCounterAuxiliaryTrackInformation() = default;
  ~GateIntegerCounterAuxiliaryTrackInformation() override = default;

  void Increment() { fCount++; }
  void SetCount(int count) { fCount = count; }
  int GetCount() const { return fCount; }

protected:
  int fCount{0};
};

#endif // GateAuxiliaryTrackInformation_h
