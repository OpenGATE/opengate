/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#ifndef GateVAuxiliaryAttribute_h
#define GateVAuxiliaryAttribute_h

#include "GateTrackData.h"
#include "G4Step.hh"
#include "G4Track.hh"
#include "G4Cache.hh"
#include "GateHelpers.h"
#include "GateUserTrackInformation.h"
#include "GateUniqueVolumeID.h"
#include <map>
#include <pybind11/pybind11.h>
#include <pybind11/stl.h>
#include <set>
#include <sstream>

namespace py = pybind11;

/*
 * Base class for simulation-level runtime attributes that are exposed through
 * a named, typed getter interface.
 *
 * A concrete auxiliary attribute may use only a subset of the mechanisms
 * provided here:
 * - typed runtime getters, which are the core public interface
 * - optional Geant4 hooks (stepping/tracking)
 * - optional per-track storage using GateUserTrackInformation slot data
 * - optional DigiAttribute exposure for ROOT-backed actors
 * - optional current-step memoization for attributes whose current-step value
 *   may be queried before their explicit Geant4 hook is invoked
 *
 * The registry managed by this class is non-owning. Ownership stays with the
 * simulation-side objects that created the attributes, and resolved pointers
 * are valid only during engine lifetime.
 */
class GateVAuxiliaryAttribute {
public:
  explicit GateVAuxiliaryAttribute(py::dict &user_info);
  virtual ~GateVAuxiliaryAttribute() = default;

  virtual void InitializeUserInfo(py::dict &user_info);
  virtual void InitializeCpp();

  void AddActions(std::set<std::string> &actions);
  bool HasAction(const std::string &action) const;

  std::string GetName() const { return fName; }
  int GetTrackDataSlotID() const { return fTrackDataSlotID; }
  char GetDigiAttributeType() const { return fDigiAttributeType; }
  virtual double GetDValue(const G4Step *step) const;
  virtual int GetIValue(const G4Step *step) const;
  virtual int64_t GetLValue(const G4Step *step) const;
  virtual std::string GetSValue(const G4Step *step) const;
  virtual G4ThreeVector Get3Value(const G4Step *step) const;
  virtual GateUniqueVolumeID::Pointer GetUValue(const G4Step *step) const;

  virtual void PreUserTrackingAction(const G4Track *track);
  virtual void PostUserTrackingAction(const G4Track *track);
  virtual void SteppingAction(const G4Step *step);

  static void ClearRegistry();
  static GateVAuxiliaryAttribute *
  GetAuxiliaryAttributeByName(const std::string &name);

protected:
  bool IsStepInVolume(const G4Step *step, const std::string &volume_name) const;
  std::string GetTrackDataValueTypeName() const;
  // Some attributes are queried from ProcessHits before their explicit
  // G4UserSteppingAction hook runs. These helpers memoize a current-step value
  // per worker thread so getters can provide same-step semantics without
  // turning actor reads into hidden state-transition hooks.
  void ResetCurrentStepValueCache() const;
  bool TryGetCachedCurrentStepIValue(const G4Step *step, int &value) const;
  void CacheCurrentStepIValue(const G4Step *step, int value) const;
  bool TryGetCachedCurrentStepDValue(const G4Step *step, double &value) const;
  void CacheCurrentStepDValue(const G4Step *step, double value) const;
  bool TryGetCachedCurrentStepLValue(const G4Step *step, int64_t &value) const;
  void CacheCurrentStepLValue(const G4Step *step, int64_t value) const;
  bool TryGetCachedCurrentStepSValue(const G4Step *step,
                                     std::string &value) const;
  void CacheCurrentStepSValue(const G4Step *step,
                              const std::string &value) const;
  bool TryGetCachedCurrentStep3Value(const G4Step *step,
                                     G4ThreeVector &value) const;
  void CacheCurrentStep3Value(const G4Step *step,
                              const G4ThreeVector &value) const;
  bool TryGetCachedCurrentStepUValue(const G4Step *step,
                                     GateUniqueVolumeID::Pointer &value) const;
  void CacheCurrentStepUValue(const G4Step *step,
                              GateUniqueVolumeID::Pointer value) const;

  template <typename TrackDataType>
  TrackDataType *GetTrackData(const G4Track *track) const {
    auto *track_state = GetGateUserTrackInformation(track);
    if (track_state == nullptr)
      return nullptr;
    auto *typed_track_data =
        track_state->GetTrackData<TrackDataType>(fTrackDataSlotID);
    if (typed_track_data == nullptr)
      return nullptr;
    if (dynamic_cast<GateVTrackData *>(typed_track_data) == nullptr) {
      std::ostringstream oss;
      oss << "Track data for attribute '" << fName << "' has an unexpected "
          << "type.";
      Fatal(oss.str());
    }
    return typed_track_data;
  }

  template <typename TrackDataType>
  TrackDataType *GetOrCreateTrackData(const G4Track *track) const {
    auto *track_state = GetOrCreateGateUserTrackInformation(track);
    return track_state->GetOrCreateTrackData<TrackDataType>(fTrackDataSlotID);
  }

  template <typename TrackDataType, typename ValueType>
  ValueType GetTrackDataValue(
      const G4Track *track, ValueType default_value,
      ValueType (TrackDataType::*getter)() const) const {
    const auto *track_data = GetTrackData<TrackDataType>(track);
    if (track_data == nullptr)
      return default_value;
    return (track_data->*getter)();
  }

  template <typename TrackDataType, typename ValueType>
  ValueType GetTrackDataValue(const G4Step *step, ValueType default_value,
                              ValueType (TrackDataType::*getter)() const) const {
    if (step == nullptr)
      return default_value;
    return GetTrackDataValue<TrackDataType, ValueType>(step->GetTrack(),
                                                       default_value, getter);
  }

  template <typename TrackDataType, typename ValueType>
  ValueType GetStoredTrackDataValue(const G4Track *track,
                                    ValueType default_value) const {
    return GetTrackDataValue<TrackDataType, ValueType>(track, default_value,
                                                       &TrackDataType::GetValue);
  }

  template <typename TrackDataType, typename ValueType>
  ValueType GetStoredTrackDataValue(const G4Step *step,
                                    ValueType default_value) const {
    return GetTrackDataValue<TrackDataType, ValueType>(step, default_value,
                                                       &TrackDataType::GetValue);
  }

  template <typename TrackDataType, typename ValueType>
  void SetStoredTrackDataValue(const G4Track *track,
                               const ValueType &value) const {
    auto *track_data = GetOrCreateTrackData<TrackDataType>(track);
    track_data->SetValue(value);
  }

  template <typename TrackDataType, typename ValueType>
  void SetStoredTrackDataValueOnSecondariesInCurrentStep(
      const G4Step *step, const ValueType &value) const {
    if (step == nullptr)
      return;
    const auto *secondaries = step->GetSecondaryInCurrentStep();
    if (secondaries == nullptr)
      return;
    for (const auto *secondary_track : *secondaries) {
      SetStoredTrackDataValue<TrackDataType, ValueType>(secondary_track, value);
    }
  }

  template <typename TrackDataType>
  void CopyTrackData(const G4Track *source_track,
                     const G4Track *target_track) const {
    const auto *source_track_data = GetTrackData<TrackDataType>(source_track);
    if (source_track_data == nullptr)
      return;
    auto *target_track_data = GetOrCreateTrackData<TrackDataType>(target_track);
    *target_track_data = *source_track_data;
  }

  template <typename TrackDataType>
  void PropagateTrackDataToSecondariesInCurrentStep(
      const G4Step *step) const {
    if (step == nullptr)
      return;
    const auto *secondaries = step->GetSecondaryInCurrentStep();
    if (secondaries == nullptr)
      return;
    for (const auto *secondary_track : *secondaries) {
      CopyTrackData<TrackDataType>(step->GetTrack(), secondary_track);
    }
  }

  std::string fName;
  int fTrackDataSlotID{-1};
  char fDigiAttributeType{'?'};
  std::set<std::string> fActions;

  static std::map<std::string, GateVAuxiliaryAttribute *>
      fRegisteredAuxiliaryAttributes;

  struct CurrentStepValueCache {
    const G4Step *fStep{nullptr};
    bool fHasDValue{false};
    double fDValue{0.0};
    bool fHasIValue{false};
    int fIValue{0};
    bool fHasLValue{false};
    int64_t fLValue{0};
    bool fHasSValue{false};
    std::string fSValue;
    bool fHas3Value{false};
    G4ThreeVector f3Value;
    bool fHasUValue{false};
    GateUniqueVolumeID::Pointer fUValue{nullptr};
  };
  mutable G4Cache<CurrentStepValueCache> fCurrentStepValueCache;
};

#endif // GateVAuxiliaryAttribute_h
