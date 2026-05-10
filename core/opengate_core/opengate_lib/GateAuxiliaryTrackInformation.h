/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#ifndef GateAuxiliaryTrackInformation_h
#define GateAuxiliaryTrackInformation_h

#include "G4ThreeVector.hh"
#include "G4VAuxiliaryTrackInformation.hh"
#include "GateUniqueVolumeID.h"
#include <cstdint>
#include <string>

template <typename ValueType>
class GateTAuxiliaryTrackInformation : public G4VAuxiliaryTrackInformation {
public:
  GateTAuxiliaryTrackInformation() = default;
  ~GateTAuxiliaryTrackInformation() override = default;

  void SetValue(const ValueType &value) { fValue = value; }
  ValueType GetValue() const { return fValue; }

protected:
  ValueType fValue{};
};

using GateDoubleAuxiliaryTrackInformation =
    GateTAuxiliaryTrackInformation<double>;
using GateIntAuxiliaryTrackInformation = GateTAuxiliaryTrackInformation<int>;
using GateLongAuxiliaryTrackInformation =
    GateTAuxiliaryTrackInformation<int64_t>;
using GateStringAuxiliaryTrackInformation =
    GateTAuxiliaryTrackInformation<std::string>;
using GateThreeVectorAuxiliaryTrackInformation =
    GateTAuxiliaryTrackInformation<G4ThreeVector>;
using GateUniqueVolumeIDAuxiliaryTrackInformation =
    GateTAuxiliaryTrackInformation<GateUniqueVolumeID::Pointer>;

class GateIntegerCounterAuxiliaryTrackInformation
    : public GateIntAuxiliaryTrackInformation {
public:
  GateIntegerCounterAuxiliaryTrackInformation() = default;
  ~GateIntegerCounterAuxiliaryTrackInformation() override = default;

  void Increment() { SetValue(GetValue() + 1); }
  void SetCount(int count) { SetValue(count); }
  int GetCount() const { return GetValue(); }
};

#endif // GateAuxiliaryTrackInformation_h
