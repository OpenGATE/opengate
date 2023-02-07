/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#include "GateTDigiAttribute.h"
#include "G4RootAnalysisManager.hh"
#include "GateDigiCollectionsRootManager.h"

template <>
GateTDigiAttribute<double>::GateTDigiAttribute(std::string vname)
    : GateVDigiAttribute(vname, 'D') {
  InitDefaultProcessHitsFunction();
}

template <>
GateTDigiAttribute<int>::GateTDigiAttribute(std::string vname)
    : GateVDigiAttribute(vname, 'I') {
  InitDefaultProcessHitsFunction();
}

template <>
GateTDigiAttribute<std::string>::GateTDigiAttribute(std::string vname)
    : GateVDigiAttribute(vname, 'S') {
  InitDefaultProcessHitsFunction();
}

template <>
GateTDigiAttribute<G4ThreeVector>::GateTDigiAttribute(std::string vname)
    : GateVDigiAttribute(vname, '3') {
  InitDefaultProcessHitsFunction();
}

template <>
GateTDigiAttribute<GateUniqueVolumeID::Pointer>::GateTDigiAttribute(
    std::string vname)
    : GateVDigiAttribute(vname, 'U') {
  InitDefaultProcessHitsFunction();
}

template <> void GateTDigiAttribute<double>::FillDigiWithEmptyValue() {
  threadLocalData.Get().fValues.push_back(0.0);
}

template <> void GateTDigiAttribute<int>::FillDigiWithEmptyValue() {
  threadLocalData.Get().fValues.push_back(0);
}

template <> void GateTDigiAttribute<std::string>::FillDigiWithEmptyValue() {
  threadLocalData.Get().fValues.push_back("");
}

template <> void GateTDigiAttribute<G4ThreeVector>::FillDigiWithEmptyValue() {
  threadLocalData.Get().fValues.push_back(G4ThreeVector());
}

template <>
void GateTDigiAttribute<GateUniqueVolumeID::Pointer>::FillDigiWithEmptyValue() {
  auto t = GateUniqueVolumeID::New();
  threadLocalData.Get().fValues.push_back(t);
}

template <> void GateTDigiAttribute<double>::FillDValue(double value) {
  threadLocalData.Get().fValues.push_back(value);
}

template <>
void GateTDigiAttribute<std::string>::FillSValue(std::string value) {
  threadLocalData.Get().fValues.push_back(value);
}

template <> void GateTDigiAttribute<int>::FillIValue(int value) {
  threadLocalData.Get().fValues.push_back(value);
}

template <>
void GateTDigiAttribute<G4ThreeVector>::Fill3Value(G4ThreeVector value) {
  threadLocalData.Get().fValues.push_back(value);
}

template <>
void GateTDigiAttribute<GateUniqueVolumeID::Pointer>::FillUValue(
    GateUniqueVolumeID::Pointer value) {
  threadLocalData.Get().fValues.push_back(value);
}

template <> void GateTDigiAttribute<double>::FillToRoot(size_t index) const {
  auto *ram = G4RootAnalysisManager::Instance();
  auto v = threadLocalData.Get().fValues[index];
  ram->FillNtupleDColumn(fTupleId, fDigiAttributeId, v);
}

template <> void GateTDigiAttribute<int>::FillToRoot(size_t index) const {
  auto *ram = G4RootAnalysisManager::Instance();
  auto v = threadLocalData.Get().fValues[index];
  ram->FillNtupleIColumn(fTupleId, fDigiAttributeId, v);
}

template <>
void GateTDigiAttribute<std::string>::FillToRoot(size_t index) const {
  auto *ram = G4RootAnalysisManager::Instance();
  auto v = threadLocalData.Get().fValues[index];
  ram->FillNtupleSColumn(fTupleId, fDigiAttributeId, v);
}

template <>
void GateTDigiAttribute<G4ThreeVector>::FillToRoot(size_t index) const {
  auto *ram = G4RootAnalysisManager::Instance();
  auto v = threadLocalData.Get().fValues[index];
  ram->FillNtupleDColumn(fTupleId, fDigiAttributeId, v[0]);
  ram->FillNtupleDColumn(fTupleId, fDigiAttributeId + 1, v[1]);
  ram->FillNtupleDColumn(fTupleId, fDigiAttributeId + 2, v[2]);
}

template <>
void GateTDigiAttribute<GateUniqueVolumeID::Pointer>::FillToRoot(
    size_t index) const {
  auto *ram = G4RootAnalysisManager::Instance();
  auto v = threadLocalData.Get().fValues[index]->fID;
  ram->FillNtupleSColumn(fTupleId, fDigiAttributeId, v);
}

template <> std::vector<double> &GateTDigiAttribute<double>::GetDValues() {
  return threadLocalData.Get().fValues;
}

template <> std::vector<int> &GateTDigiAttribute<int>::GetIValues() {
  return threadLocalData.Get().fValues;
}

template <>
std::vector<std::string> &GateTDigiAttribute<std::string>::GetSValues() {
  return threadLocalData.Get().fValues;
}

template <>
std::vector<G4ThreeVector> &GateTDigiAttribute<G4ThreeVector>::Get3Values() {
  return threadLocalData.Get().fValues;
}

template <>
std::vector<GateUniqueVolumeID::Pointer> &
GateTDigiAttribute<GateUniqueVolumeID::Pointer>::GetUValues() {
  return threadLocalData.Get().fValues;
}
