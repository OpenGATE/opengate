/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#include "GateHitAttributeManager.h"
#include "GateTHitAttribute.h"

GateHitAttributeManager *GateHitAttributeManager::fInstance = nullptr;

GateHitAttributeManager *GateHitAttributeManager::GetInstance() {
  if (fInstance == nullptr)
    fInstance = new GateHitAttributeManager();
  return fInstance;
}

GateHitAttributeManager::GateHitAttributeManager() {
  InitializeAllHitAttributes();
}

GateVHitAttribute *GateHitAttributeManager::NewHitAttribute(std::string name) {
  if (fAvailableHitAttributes.find(name) == fAvailableHitAttributes.end()) {
    std::ostringstream oss;
    oss << "Error the attribute named '" << name << "' does not exists. Abort";
    oss << " List of available attributes : "
        << DumpAvailableHitAttributeNames();
    Fatal(oss.str());
  }
  return CopyHitAttribute(fAvailableHitAttributes[name]);
}

std::string GateHitAttributeManager::DumpAvailableHitAttributeNames() {
  std::ostringstream oss;
  for (const auto &branch : fAvailableHitAttributes)
    oss << branch.second->GetHitAttributeName() << " ";
  return oss.str();
}

std::vector<std::string>
GateHitAttributeManager::GetAvailableHitAttributeNames() {
  std::vector<std::string> list;
  for (const auto &branch : fAvailableHitAttributes)
    list.push_back(branch.second->GetHitAttributeName());
  return list;
}

GateVHitAttribute *
GateHitAttributeManager::GetHitAttributeByName(const std::string &name) {
  try {
    return fAvailableHitAttributes[name];
  } catch (std::exception &) {
    std::ostringstream oss;
    oss << "The attribute named '" << name
        << "' does not exist. List of available attributes: "
        << DumpAvailableHitAttributeNames();
    Fatal(oss.str());
  }
  return nullptr; // to avoid warning
}

void GateHitAttributeManager::DefineHitAttribute(
    std::string name, char type,
    const GateVHitAttribute::ProcessHitsFunctionType &f) {
  GateVHitAttribute *att = nullptr;
  if (type == 'D')
    att = new GateTHitAttribute<double>(name);
  if (type == 'I')
    att = new GateTHitAttribute<int>(name);
  if (type == 'S')
    att = new GateTHitAttribute<std::string>(name);
  if (type == '3')
    att = new GateTHitAttribute<G4ThreeVector>(name);
  if (type == 'U')
    att = new GateTHitAttribute<GateUniqueVolumeID::Pointer>(name);
  if (att == nullptr) {
    std::ostringstream oss;
    oss << "Error while defining HitAttribute " << name << " the type '" << type
        << "' is unknown.";
    Fatal(oss.str());
  } else {
    att->fProcessHitsFunction = f;
    fAvailableHitAttributes[att->GetHitAttributeName()] = att;
  }
}

GateVHitAttribute *
GateHitAttributeManager::CopyHitAttribute(GateVHitAttribute *att) {
  GateVHitAttribute *a = nullptr;
  if (att->GetHitAttributeType() == 'D') {
    a = new GateTHitAttribute<double>(att->GetHitAttributeName());
  }
  if (att->GetHitAttributeType() == 'I') {
    a = new GateTHitAttribute<int>(att->GetHitAttributeName());
  }
  if (att->GetHitAttributeType() == 'S') {
    a = new GateTHitAttribute<std::string>(att->GetHitAttributeName());
  }
  if (att->GetHitAttributeType() == '3') {
    a = new GateTHitAttribute<G4ThreeVector>(att->GetHitAttributeName());
  }
  if (att->GetHitAttributeType() == 'U') {
    a = new GateTHitAttribute<GateUniqueVolumeID::Pointer>(
        att->GetHitAttributeName());
  }
  if (a != nullptr) {
    a->fProcessHitsFunction = att->fProcessHitsFunction;
    return a;
  }
  DDD(att->GetHitAttributeName());
  DDD(att->GetHitAttributeType());
  DDD(att->GetHitAttributeTupleId());
  Fatal("Error in CopyHitAttribute");
  return nullptr;
}
