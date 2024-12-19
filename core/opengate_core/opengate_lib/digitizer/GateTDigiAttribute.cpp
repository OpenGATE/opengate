/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#include "GateTDigiAttribute.h"
#include "G4RootAnalysisManager.hh"
#include "GateDigiCollectionsRootManager.h"

template <class T>
GateTDigiAttribute<T>::GateTDigiAttribute(std::string vname)
    : GateVDigiAttribute(vname, 'D') {
  DDE(typeid(T).name());
  DDE(vname);
  Fatal("GateTDigiAttribute constructor must be specialized for this type");
}

template <class T>
void GateTDigiAttribute<T>::InitDefaultProcessHitsFunction() {
  // By default, "do nothing" in the process hit function
  fProcessHitsFunction = [=](GateVDigiAttribute *att, G4Step *) {};
}

template <class T> int GateTDigiAttribute<T>::GetSize() const {
  return threadLocalData.Get().fValues.size();
}

template <class T> void GateTDigiAttribute<T>::FillDValue(double) {
  DDE(fDigiAttributeType);
  DDE(fDigiAttributeName);
  Fatal("Cannot use FillDValue for this type");
}

template <class T> void GateTDigiAttribute<T>::FillSValue(std::string) {
  DDE(fDigiAttributeType);
  DDE(fDigiAttributeName);
  Fatal("Cannot use FillSValue for this type");
}

template <class T> void GateTDigiAttribute<T>::FillIValue(int) {
  DDE(fDigiAttributeType);
  DDE(fDigiAttributeName);
  Fatal("Cannot use FillIValue for this type");
}

template <class T> void GateTDigiAttribute<T>::Fill3Value(G4ThreeVector) {
  DDE(fDigiAttributeType);
  DDE(fDigiAttributeName);
  Fatal("Cannot use Fill3Value for this type");
}

template <class T>
void GateTDigiAttribute<T>::FillUValue(GateUniqueVolumeID::Pointer) {
  DDE(fDigiAttributeType);
  DDE(fDigiAttributeName);
  Fatal("Cannot use FillUValue for this type");
}

template <class T> std::vector<double> &GateTDigiAttribute<T>::GetDValues() {
  Fatal("Cannot use GetDValues for this type, GateTDigiAttribute<T> D");
  return *(new std::vector<double>); // to avoid warning
}

template <class T> std::vector<int> &GateTDigiAttribute<T>::GetIValues() {
  Fatal("Cannot use GetDValues for this type, GateTDigiAttribute<T> I");
  return *(new std::vector<int>); // to avoid warning
}

template <class T>
std::vector<std::string> &GateTDigiAttribute<T>::GetSValues() {
  Fatal("Cannot use GetDValues for this type, GateTDigiAttribute<T> S");
  return *(new std::vector<std::string>); // to avoid warning
}

template <class T>
std::vector<G4ThreeVector> &GateTDigiAttribute<T>::Get3Values() {
  Fatal("Cannot use GetDValues for this type, GateTDigiAttribute<T> 3");
  return *(new std::vector<G4ThreeVector>); // to avoid warning
}

template <class T>
std::vector<GateUniqueVolumeID::Pointer> &GateTDigiAttribute<T>::GetUValues() {
  Fatal("Cannot use GetDValues for this type, GateTDigiAttribute<T> U");
  return *(new std::vector<GateUniqueVolumeID::Pointer>); // to avoid warning
}

template <class T> void GateTDigiAttribute<T>::Clear() {
  threadLocalData.Get().fValues.clear();
}

template <class T>
const std::vector<T> &GateTDigiAttribute<T>::GetValues() const {
  return threadLocalData.Get().fValues;
}

template <class T>
void GateTDigiAttribute<T>::Fill(GateVDigiAttribute *input, size_t index) {
  // we assume that the given GateVDigiAttribute has the same type
  auto tinput = static_cast<GateTDigiAttribute<T> *>(input);
  threadLocalData.Get().fValues.push_back(tinput->GetValues()[index]);
}

template <class T> void GateTDigiAttribute<T>::FillDigiWithEmptyValue() {
  DDE(fDigiAttributeType);
  DDE(fDigiAttributeName);
  Fatal("Must not be here, FillDigiWithEmptyValue must be specialized for this "
        "type");
}

template <class T>
void GateTDigiAttribute<T>::FillToRoot(size_t /*index*/) const {
  DDE(fDigiAttributeType);
  DDE(fDigiAttributeName);
  Fatal(
      "Must not be here, FillToRootIfNeeded must be specialized for this type");
}

template <class T> std::string GateTDigiAttribute<T>::Dump(int i) const {
  std::ostringstream oss;
  oss << threadLocalData.Get().fValues[i];
  return oss.str();
}

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

#if defined(WIN32) || defined(_WIN32) ||                                       \
    defined(__WIN32) && !defined(__CYGWIN__)
template GateTDigiAttribute<double>;
template GateTDigiAttribute<int>;
template GateTDigiAttribute<std::string>;
template GateTDigiAttribute<G4ThreeVector>;
template GateTDigiAttribute<GateUniqueVolumeID::Pointer>;
#endif
