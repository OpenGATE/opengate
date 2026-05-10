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
int GateVAuxiliaryAttribute::fNextAuxiliaryAttributeID = -1;

GateVAuxiliaryAttribute::GateVAuxiliaryAttribute(py::dict &user_info) {
  InitializeUserInfo(user_info);
}

void GateVAuxiliaryAttribute::InitializeUserInfo(py::dict &user_info) {
  fName = DictGetStr(user_info, "name");
}

void GateVAuxiliaryAttribute::InitializeCpp() {
  fTrackInfoID = RegisterAuxiliaryAttributeName(fName);
}

void GateVAuxiliaryAttribute::AddActions(std::set<std::string> &actions) {
  fActions.insert(actions.begin(), actions.end());
}

bool GateVAuxiliaryAttribute::HasAction(const std::string &action) const {
  return fActions.find(action) != fActions.end();
}

void GateVAuxiliaryAttribute::PreUserTrackingAction(const G4Track *) {}

void GateVAuxiliaryAttribute::PostUserTrackingAction(const G4Track *) {}

void GateVAuxiliaryAttribute::SteppingAction(const G4Step *) {}

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
