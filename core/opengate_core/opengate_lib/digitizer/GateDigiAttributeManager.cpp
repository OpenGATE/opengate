/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#include "GateDigiAttributeManager.h"
#include "GateTDigiAttribute.h"

GateDigiAttributeManager *GateDigiAttributeManager::fInstance = nullptr;

GateDigiAttributeManager *GateDigiAttributeManager::GetInstance() {
  if (fInstance == nullptr)
    fInstance = new GateDigiAttributeManager();
  return fInstance;
}

GateDigiAttributeManager::GateDigiAttributeManager() {
  InitializeAllDigiAttributes();
}

GateVDigiAttribute *
GateDigiAttributeManager::GetDigiAttribute(std::string name) {
  if (fAvailableDigiAttributes.find(name) == fAvailableDigiAttributes.end()) {
    std::ostringstream oss;
    oss << "Error the attribute named '" << name << "' does not exists. Abort";
    oss << " List of available attributes : "
        << DumpAvailableDigiAttributeNames();
    Fatal(oss.str());
  }
  return CopyDigiAttribute(fAvailableDigiAttributes[name]);
}

std::string GateDigiAttributeManager::DumpAvailableDigiAttributeNames() {
  std::ostringstream oss;
  for (const auto &branch : fAvailableDigiAttributes)
    oss << branch.second->GetDigiAttributeName() << " ";
  return oss.str();
}

std::vector<std::string>
GateDigiAttributeManager::GetAvailableDigiAttributeNames() {
  std::vector<std::string> list;
  for (const auto &branch : fAvailableDigiAttributes)
    list.push_back(branch.second->GetDigiAttributeName());
  return list;
}

GateVDigiAttribute *
GateDigiAttributeManager::GetDigiAttributeByName(const std::string &name) {
  try {
    return fAvailableDigiAttributes[name];
  } catch (std::exception &) {
    std::ostringstream oss;
    oss << "The attribute named '" << name
        << "' does not exist. List of available attributes: "
        << DumpAvailableDigiAttributeNames();
    Fatal(oss.str());
  }
  return nullptr; // to avoid warning
}

void GateDigiAttributeManager::DefineDigiAttribute(
    std::string name, char type,
    const GateVDigiAttribute::ProcessHitsFunctionType &f) {
  GateVDigiAttribute *att = nullptr;
  if (type == 'D')
    att = new GateTDigiAttribute<double>(name);
  if (type == 'I')
    att = new GateTDigiAttribute<int>(name);

  if (type == 'S')
    att = new GateTDigiAttribute<std::string>(name);
  if (type == '3')
    att = new GateTDigiAttribute<G4ThreeVector>(name);
  if (type == 'U')
    att = new GateTDigiAttribute<GateUniqueVolumeID::Pointer>(name);
  if (att == nullptr) {
    std::ostringstream oss;
    oss << "Error while defining DigiAttribute " << name << " the type '"
        << type << "' is unknown.";
    Fatal(oss.str());
  } else {
    att->fProcessHitsFunction = f;
    fAvailableDigiAttributes[att->GetDigiAttributeName()] = att;
  }
}

GateVDigiAttribute *GateDigiAttributeManager::CopyDigiAttribute(
    GateVDigiAttribute *att) { // FIXME to move elsewhere !!!!!
  GateVDigiAttribute *a = nullptr;
  if (att->GetDigiAttributeType() == 'D') {
    a = new GateTDigiAttribute<double>(att->GetDigiAttributeName());
  }
  if (att->GetDigiAttributeType() == 'I') {
    a = new GateTDigiAttribute<int>(att->GetDigiAttributeName());
  }
  if (att->GetDigiAttributeType() == 'S') {
    a = new GateTDigiAttribute<std::string>(att->GetDigiAttributeName());
  }
  if (att->GetDigiAttributeType() == '3') {
    a = new GateTDigiAttribute<G4ThreeVector>(att->GetDigiAttributeName());
  }
  if (att->GetDigiAttributeType() == 'U') {
    a = new GateTDigiAttribute<GateUniqueVolumeID::Pointer>(
        att->GetDigiAttributeName());
  }
  if (a != nullptr) {
    a->fProcessHitsFunction = att->fProcessHitsFunction;
    return a;
  }
  DDE(att->GetDigiAttributeName());
  DDE(att->GetDigiAttributeType());
  DDE(att->GetDigiAttributeTupleId());
  Fatal("Error in CopyDigiAttribute");
  return nullptr;
}
