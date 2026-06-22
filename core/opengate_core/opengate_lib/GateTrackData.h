/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#ifndef GateTrackData_h
#define GateTrackData_h

#include "GateUniqueVolumeID.h"
#include <G4ThreeVector.hh>
#include <cstdint>
#include <string>

/*
 * Typed payloads stored inside GateUserTrackInformation's slot map.
 *
 * These are lightweight, track-owned value containers. They can be fed and
 * consumed by attributes, actors, or biasing operators, depending on which
 * component owns the associated slot.
 */
class GateVTrackData {
public:
  GateVTrackData() = default;
  virtual ~GateVTrackData() = default;
};

template <typename ValueType> class GateTTrackData : public GateVTrackData {
public:
  GateTTrackData() = default;
  ~GateTTrackData() override = default;

  void SetValue(const ValueType &value) { fValue = value; }
  ValueType GetValue() const { return fValue; }

protected:
  ValueType fValue{};
};

using GateDoubleTrackData = GateTTrackData<double>;
using GateIntTrackData = GateTTrackData<int>;
using GateLongTrackData = GateTTrackData<int64_t>;
using GateStringTrackData = GateTTrackData<std::string>;
using GateThreeVectorTrackData = GateTTrackData<G4ThreeVector>;
using GateUniqueVolumeIDTrackData = GateTTrackData<GateUniqueVolumeID::Pointer>;

class GateIntegerCounterTrackData : public GateIntTrackData {
public:
  GateIntegerCounterTrackData() = default;
  ~GateIntegerCounterTrackData() override = default;

  void Increment() { SetValue(GetValue() + 1); }
  void SetCount(int count) { SetValue(count); }
  int GetCount() const { return GetValue(); }
};

#endif // GateTrackData_h
