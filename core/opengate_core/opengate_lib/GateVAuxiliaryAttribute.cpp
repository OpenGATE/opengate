/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#include "GateVAuxiliaryAttribute.h"
#include "GateHelpersDict.h"

class GateAuxiliaryAttributeMapInitializer
    : public G4VAuxiliaryTrackInformation {
public:
  GateAuxiliaryAttributeMapInitializer() = default;
  ~GateAuxiliaryAttributeMapInitializer() override = default;
};

std::map<std::string, int>
    GateVAuxiliaryAttribute::fRegisteredAuxiliaryAttributeIDs;
std::map<std::string, GateVAuxiliaryAttribute *>
    GateVAuxiliaryAttribute::fRegisteredAuxiliaryAttributes;
int GateVAuxiliaryAttribute::fNextAuxiliaryAttributeID = -1;

GateVAuxiliaryAttribute::GateVAuxiliaryAttribute(py::dict &user_info) {
  InitializeUserInfo(user_info);
}

void GateVAuxiliaryAttribute::InitializeUserInfo(py::dict &user_info) {
  fName = DictGetStr(user_info, "name");
}

void GateVAuxiliaryAttribute::InitializeCpp() {
  fTrackInfoID = RegisterAuxiliaryAttributeName(fName);
  fRegisteredAuxiliaryAttributes[fName] = this;
}

void GateVAuxiliaryAttribute::AddActions(std::set<std::string> &actions) {
  fActions.insert(actions.begin(), actions.end());
}

bool GateVAuxiliaryAttribute::HasAction(const std::string &action) const {
  return fActions.find(action) != fActions.end();
}

double GateVAuxiliaryAttribute::GetDValue(const G4Step *) const {
  Fatal("Auxiliary attribute '" + fName + "' does not provide a double value.");
  return 0.0;
}

int GateVAuxiliaryAttribute::GetIValue(const G4Step *) const {
  Fatal("Auxiliary attribute '" + fName + "' does not provide an int value.");
  return 0;
}

int64_t GateVAuxiliaryAttribute::GetLValue(const G4Step *) const {
  Fatal("Auxiliary attribute '" + fName + "' does not provide an int64 value.");
  return 0;
}

std::string GateVAuxiliaryAttribute::GetSValue(const G4Step *) const {
  Fatal("Auxiliary attribute '" + fName + "' does not provide a string value.");
  return "";
}

G4ThreeVector GateVAuxiliaryAttribute::Get3Value(const G4Step *) const {
  Fatal("Auxiliary attribute '" + fName +
        "' does not provide a G4ThreeVector value.");
  return {};
}

GateUniqueVolumeID::Pointer
GateVAuxiliaryAttribute::GetUValue(const G4Step *) const {
  Fatal("Auxiliary attribute '" + fName +
        "' does not provide a GateUniqueVolumeID value.");
  return nullptr;
}

void GateVAuxiliaryAttribute::PreUserTrackingAction(const G4Track *) {}

void GateVAuxiliaryAttribute::PostUserTrackingAction(const G4Track *) {}

void GateVAuxiliaryAttribute::SteppingAction(const G4Step *) {}

void GateVAuxiliaryAttribute::ClearRegistry() {
  fRegisteredAuxiliaryAttributes.clear();
}

GateVAuxiliaryAttribute *
GateVAuxiliaryAttribute::GetAuxiliaryAttributeByName(const std::string &name) {
  const auto it = fRegisteredAuxiliaryAttributes.find(name);
  if (it == fRegisteredAuxiliaryAttributes.end())
    return nullptr;
  return it->second;
}

int GateVAuxiliaryAttribute::RegisterAuxiliaryAttributeName(
    const std::string &name) const {
  const auto it = fRegisteredAuxiliaryAttributeIDs.find(name);
  if (it != fRegisteredAuxiliaryAttributeIDs.end())
    return it->second;
  const auto id = fNextAuxiliaryAttributeID;
  fNextAuxiliaryAttributeID--;
  fRegisteredAuxiliaryAttributeIDs[name] = id;
  return id;
}

G4VAuxiliaryTrackInformation *
GateVAuxiliaryAttribute::GetAuxiliaryTrackInformation(
    const G4Track *track) const {
  if (track == nullptr)
    return nullptr;
  return track->GetAuxiliaryTrackInformation(fTrackInfoID);
}

void GateVAuxiliaryAttribute::SetAuxiliaryTrackInformation(
    const G4Track *track, G4VAuxiliaryTrackInformation *track_info) const {
  if (track == nullptr)
    return;
  auto *info_map = track->GetAuxiliaryTrackInformationMap();
  if (info_map == nullptr) {
    /*
     * Geant4 11.x validates SetAuxiliaryTrackInformation() IDs against the
     * closed G4PhysicsModelCatalog. We use OpenGATE-owned negative IDs, so we
     * only use a valid built-in model ID to force Geant4 to allocate the map,
     * then remove and delete the temporary entry before inserting ours.
     */
    constexpr int modelEMID = 10000;
    auto *initializer = new GateAuxiliaryAttributeMapInitializer();
    track->SetAuxiliaryTrackInformation(modelEMID, initializer);
    const_cast<G4Track *>(track)->RemoveAuxiliaryTrackInformation(modelEMID);
    delete initializer;
    info_map = track->GetAuxiliaryTrackInformationMap();
  }
  (*info_map)[fTrackInfoID] = track_info;
}

bool GateVAuxiliaryAttribute::IsStepInVolume(
    const G4Step *step, const std::string &volume_name) const {
  /*
   * TODO: This recursive touchable-history check is simple and correct, but it
   * is likely not the most efficient option for hot stepping paths. Consider a
   * volume-sensitive auxiliary-attribute base class that resolves the
   * configured volume once, precomputes the set of descendant logical volumes,
   * and then performs a direct membership test on the current pre-step logical
   * volume instead of walking the touchable hierarchy on every step.
   */
  if (step == nullptr)
    return false;
  const auto *pre_step_point = step->GetPreStepPoint();
  if (pre_step_point == nullptr)
    return false;
  const auto &touchable = pre_step_point->GetTouchableHandle();
  if (touchable->GetVolume() == nullptr)
    return false;
  const auto history_depth = touchable->GetHistoryDepth();
  for (int depth = 0; depth <= history_depth; depth++) {
    const auto *physical_volume = touchable->GetVolume(depth);
    if (physical_volume != nullptr &&
        physical_volume->GetLogicalVolume()->GetName() == volume_name) {
      return true;
    }
  }
  return false;
}

void GateVAuxiliaryAttribute::ResetCurrentStepValueCache() const {
  auto &cache = fCurrentStepValueCache.Get();
  cache.fStep = nullptr;
  cache.fHasDValue = false;
  cache.fHasIValue = false;
  cache.fHasLValue = false;
  cache.fHasSValue = false;
  cache.fHas3Value = false;
  cache.fHasUValue = false;
  cache.fSValue.clear();
  cache.fUValue = nullptr;
}

bool GateVAuxiliaryAttribute::TryGetCachedCurrentStepIValue(const G4Step *step,
                                                            int &value) const {
  const auto &cache = fCurrentStepValueCache.Get();
  if (cache.fStep != step || !cache.fHasIValue)
    return false;
  value = cache.fIValue;
  return true;
}

void GateVAuxiliaryAttribute::CacheCurrentStepIValue(const G4Step *step,
                                                     int value) const {
  auto &cache = fCurrentStepValueCache.Get();
  if (cache.fStep != step) {
    ResetCurrentStepValueCache();
    cache.fStep = step;
  }
  cache.fHasIValue = true;
  cache.fIValue = value;
}

bool GateVAuxiliaryAttribute::TryGetCachedCurrentStepDValue(
    const G4Step *step, double &value) const {
  const auto &cache = fCurrentStepValueCache.Get();
  if (cache.fStep != step || !cache.fHasDValue)
    return false;
  value = cache.fDValue;
  return true;
}

void GateVAuxiliaryAttribute::CacheCurrentStepDValue(const G4Step *step,
                                                     double value) const {
  auto &cache = fCurrentStepValueCache.Get();
  if (cache.fStep != step) {
    ResetCurrentStepValueCache();
    cache.fStep = step;
  }
  cache.fHasDValue = true;
  cache.fDValue = value;
}

bool GateVAuxiliaryAttribute::TryGetCachedCurrentStepLValue(
    const G4Step *step, int64_t &value) const {
  const auto &cache = fCurrentStepValueCache.Get();
  if (cache.fStep != step || !cache.fHasLValue)
    return false;
  value = cache.fLValue;
  return true;
}

void GateVAuxiliaryAttribute::CacheCurrentStepLValue(const G4Step *step,
                                                     int64_t value) const {
  auto &cache = fCurrentStepValueCache.Get();
  if (cache.fStep != step) {
    ResetCurrentStepValueCache();
    cache.fStep = step;
  }
  cache.fHasLValue = true;
  cache.fLValue = value;
}

bool GateVAuxiliaryAttribute::TryGetCachedCurrentStepSValue(
    const G4Step *step, std::string &value) const {
  const auto &cache = fCurrentStepValueCache.Get();
  if (cache.fStep != step || !cache.fHasSValue)
    return false;
  value = cache.fSValue;
  return true;
}

void GateVAuxiliaryAttribute::CacheCurrentStepSValue(
    const G4Step *step, const std::string &value) const {
  auto &cache = fCurrentStepValueCache.Get();
  if (cache.fStep != step) {
    ResetCurrentStepValueCache();
    cache.fStep = step;
  }
  cache.fHasSValue = true;
  cache.fSValue = value;
}

bool GateVAuxiliaryAttribute::TryGetCachedCurrentStep3Value(
    const G4Step *step, G4ThreeVector &value) const {
  const auto &cache = fCurrentStepValueCache.Get();
  if (cache.fStep != step || !cache.fHas3Value)
    return false;
  value = cache.f3Value;
  return true;
}

void GateVAuxiliaryAttribute::CacheCurrentStep3Value(
    const G4Step *step, const G4ThreeVector &value) const {
  auto &cache = fCurrentStepValueCache.Get();
  if (cache.fStep != step) {
    ResetCurrentStepValueCache();
    cache.fStep = step;
  }
  cache.fHas3Value = true;
  cache.f3Value = value;
}

bool GateVAuxiliaryAttribute::TryGetCachedCurrentStepUValue(
    const G4Step *step, GateUniqueVolumeID::Pointer &value) const {
  const auto &cache = fCurrentStepValueCache.Get();
  if (cache.fStep != step || !cache.fHasUValue)
    return false;
  value = cache.fUValue;
  return true;
}

void GateVAuxiliaryAttribute::CacheCurrentStepUValue(
    const G4Step *step, GateUniqueVolumeID::Pointer value) const {
  auto &cache = fCurrentStepValueCache.Get();
  if (cache.fStep != step) {
    ResetCurrentStepValueCache();
    cache.fStep = step;
  }
  cache.fHasUValue = true;
  cache.fUValue = std::move(value);
}
