/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#ifndef GateVAuxiliaryAttribute_h
#define GateVAuxiliaryAttribute_h

#include "G4Step.hh"
#include "G4Track.hh"
#include "G4VAuxiliaryTrackInformation.hh"
#include "GateHelpers.h"
#include <map>
#include <pybind11/pybind11.h>
#include <pybind11/stl.h>
#include <set>
#include <sstream>

namespace py = pybind11;

class GateVAuxiliaryAttribute {
public:
  explicit GateVAuxiliaryAttribute(py::dict &user_info);
  virtual ~GateVAuxiliaryAttribute() = default;

  virtual void InitializeUserInfo(py::dict &user_info);
  virtual void InitializeCpp();

  void AddActions(std::set<std::string> &actions);
  bool HasAction(const std::string &action) const;

  std::string GetName() const { return fName; }
  int GetTrackInfoID() const { return fTrackInfoID; }
  char GetDigiAttributeType() const { return fDigiAttributeType; }

  virtual void PreUserTrackingAction(const G4Track *track);
  virtual void PostUserTrackingAction(const G4Track *track);
  virtual void SteppingAction(const G4Step *step);

protected:
  int RegisterAuxiliaryAttributeName(const std::string &name) const;
  G4VAuxiliaryTrackInformation *
  GetAuxiliaryTrackInformation(const G4Track *track) const;
  void
  SetAuxiliaryTrackInformation(const G4Track *track,
                               G4VAuxiliaryTrackInformation *track_info) const;

  template <typename TrackInformationType>
  TrackInformationType *
  GetAuxiliaryTrackInformation(const G4Track *track) const {
    auto *info = GetAuxiliaryTrackInformation(track);
    if (info == nullptr)
      return nullptr;
    auto *typed_info = dynamic_cast<TrackInformationType *>(info);
    if (typed_info == nullptr) {
      std::ostringstream oss;
      oss << "Auxiliary track information for attribute '" << fName
          << "' has an unexpected type.";
      Fatal(oss.str());
    }
    return typed_info;
  }

  template <typename TrackInformationType>
  TrackInformationType *
  GetOrCreateAuxiliaryTrackInformation(const G4Track *track) const {
    auto *info = GetAuxiliaryTrackInformation<TrackInformationType>(track);
    if (info != nullptr)
      return info;
    info = new TrackInformationType();
    SetAuxiliaryTrackInformation(track, info);
    return info;
  }

  template <typename TrackInformationType, typename ValueType>
  ValueType GetAuxiliaryTrackInformationValue(
      const G4Track *track, ValueType default_value,
      ValueType (TrackInformationType::*getter)() const) const {
    const auto *info =
        GetAuxiliaryTrackInformation<TrackInformationType>(track);
    if (info == nullptr)
      return default_value;
    return (info->*getter)();
  }

  template <typename TrackInformationType, typename ValueType>
  ValueType
  GetAuxiliaryTrackInformationValue(const G4Step *step, ValueType default_value,
                                    ValueType (TrackInformationType::*getter)()
                                        const) const {
    if (step == nullptr)
      return default_value;
    return GetAuxiliaryTrackInformationValue<TrackInformationType, ValueType>(
        step->GetTrack(), default_value, getter);
  }

  template <typename TrackInformationType>
  void CopyAuxiliaryTrackInformation(const G4Track *source_track,
                                     const G4Track *target_track) const {
    const auto *source_info =
        GetAuxiliaryTrackInformation<TrackInformationType>(source_track);
    if (source_info == nullptr)
      return;
    auto *target_info =
        GetOrCreateAuxiliaryTrackInformation<TrackInformationType>(
            target_track);
    *target_info = *source_info;
  }

  template <typename TrackInformationType>
  void PropagateAuxiliaryTrackInformationToSecondariesInCurrentStep(
      const G4Step *step) const {
    if (step == nullptr)
      return;
    const auto *secondaries = step->GetSecondaryInCurrentStep();
    if (secondaries == nullptr)
      return;
    for (const auto *secondary_track : *secondaries) {
      CopyAuxiliaryTrackInformation<TrackInformationType>(step->GetTrack(),
                                                          secondary_track);
    }
  }

  std::string fName;
  int fTrackInfoID{-1};
  char fDigiAttributeType{'?'};
  std::set<std::string> fActions;

  static std::map<std::string, int> fRegisteredAuxiliaryAttributeIDs;
  static int fNextAuxiliaryAttributeID;
};

#endif // GateVAuxiliaryAttribute_h
