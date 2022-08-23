/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#include "GateTHitAttribute.h"
#include "G4RootAnalysisManager.hh"
#include "GateHitsCollectionsRootManager.h"

template <>
GateTHitAttribute<double>::GateTHitAttribute(std::string vname)
    : GateVHitAttribute(vname, 'D') {}

template <>
GateTHitAttribute<int>::GateTHitAttribute(std::string vname)
    : GateVHitAttribute(vname, 'I') {}

template <>
GateTHitAttribute<std::string>::GateTHitAttribute(std::string vname)
    : GateVHitAttribute(vname, 'S') {}

template <>
GateTHitAttribute<G4ThreeVector>::GateTHitAttribute(std::string vname)
    : GateVHitAttribute(vname, '3') {}

template <>
GateTHitAttribute<GateUniqueVolumeID::Pointer>::GateTHitAttribute(
    std::string vname)
    : GateVHitAttribute(vname, 'U') {}

template <> void GateTHitAttribute<double>::FillHitWithEmptyValue() {
  threadLocalData.Get().fValues.push_back(0.0);
}

template <> void GateTHitAttribute<int>::FillHitWithEmptyValue() {
  threadLocalData.Get().fValues.push_back(0);
}

template <> void GateTHitAttribute<std::string>::FillHitWithEmptyValue() {
  threadLocalData.Get().fValues.push_back("");
}

template <> void GateTHitAttribute<G4ThreeVector>::FillHitWithEmptyValue() {
  threadLocalData.Get().fValues.push_back(G4ThreeVector());
}

template <>
void GateTHitAttribute<GateUniqueVolumeID::Pointer>::FillHitWithEmptyValue() {
  auto t = GateUniqueVolumeID::New();
  threadLocalData.Get().fValues.push_back(t);
}

template <> void GateTHitAttribute<double>::FillDValue(double value) {
  threadLocalData.Get().fValues.push_back(value);
}

template <> void GateTHitAttribute<std::string>::FillSValue(std::string value) {
  threadLocalData.Get().fValues.push_back(value);
}

template <> void GateTHitAttribute<int>::FillIValue(int value) {
  threadLocalData.Get().fValues.push_back(value);
}

template <>
void GateTHitAttribute<G4ThreeVector>::Fill3Value(G4ThreeVector value) {
  threadLocalData.Get().fValues.push_back(value);
}

template <>
void GateTHitAttribute<GateUniqueVolumeID::Pointer>::FillUValue(
    GateUniqueVolumeID::Pointer value) {
  threadLocalData.Get().fValues.push_back(value);
}

template <> void GateTHitAttribute<double>::FillToRoot(size_t index) const {
  auto *ram = G4RootAnalysisManager::Instance();
  auto v = threadLocalData.Get().fValues[index];
  ram->FillNtupleDColumn(fTupleId, fHitAttributeId, v);
}

template <> void GateTHitAttribute<int>::FillToRoot(size_t index) const {
  auto *ram = G4RootAnalysisManager::Instance();
  auto v = threadLocalData.Get().fValues[index];
  ram->FillNtupleIColumn(fTupleId, fHitAttributeId, v);
}

template <>
void GateTHitAttribute<std::string>::FillToRoot(size_t index) const {
  auto *ram = G4RootAnalysisManager::Instance();
  auto v = threadLocalData.Get().fValues[index];
  ram->FillNtupleSColumn(fTupleId, fHitAttributeId, v);
}

template <>
void GateTHitAttribute<G4ThreeVector>::FillToRoot(size_t index) const {
  auto *ram = G4RootAnalysisManager::Instance();
  auto v = threadLocalData.Get().fValues[index];
  ram->FillNtupleDColumn(fTupleId, fHitAttributeId, v[0]);
  ram->FillNtupleDColumn(fTupleId, fHitAttributeId + 1, v[1]);
  ram->FillNtupleDColumn(fTupleId, fHitAttributeId + 2, v[2]);
}

template <>
void GateTHitAttribute<GateUniqueVolumeID::Pointer>::FillToRoot(
    size_t index) const {
  auto *ram = G4RootAnalysisManager::Instance();
  auto v = threadLocalData.Get().fValues[index]->fID;
  ram->FillNtupleSColumn(fTupleId, fHitAttributeId, v);
}

template <> std::vector<double> &GateTHitAttribute<double>::GetDValues() {
  return threadLocalData.Get().fValues;
}

template <> std::vector<int> &GateTHitAttribute<int>::GetIValues() {
  return threadLocalData.Get().fValues;
}

template <>
std::vector<std::string> &GateTHitAttribute<std::string>::GetSValues() {
  return threadLocalData.Get().fValues;
}

template <>
std::vector<G4ThreeVector> &GateTHitAttribute<G4ThreeVector>::Get3Values() {
  return threadLocalData.Get().fValues;
}

template <>
std::vector<GateUniqueVolumeID::Pointer> &
GateTHitAttribute<GateUniqueVolumeID::Pointer>::GetUValues() {
  return threadLocalData.Get().fValues;
}
