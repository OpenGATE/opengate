/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#include "GamTHitAttribute.h"
#include "GamHitsCollectionsRootManager.h"

template<>
GamTHitAttribute<double>::GamTHitAttribute(std::string vname) :
    GamVHitAttribute(vname, 'D') {
}

template<>
GamTHitAttribute<int>::GamTHitAttribute(std::string vname) :
    GamVHitAttribute(vname, 'I') {
}

template<>
GamTHitAttribute<std::string>::GamTHitAttribute(std::string vname) :
    GamVHitAttribute(vname, 'S') {
}

template<>
GamTHitAttribute<G4ThreeVector>::GamTHitAttribute(std::string vname) :
    GamVHitAttribute(vname, '3') {
}


template<>
void GamTHitAttribute<double>::FillDValue(double value) {
    fValues.push_back(value);
}

template<>
void GamTHitAttribute<std::string>::FillSValue(std::string value) {
    fValues.push_back(value);
}

template<>
void GamTHitAttribute<int>::FillIValue(int value) {
    fValues.push_back(value);
}

template<>
void GamTHitAttribute<G4ThreeVector>::Fill3Value(G4ThreeVector value) {
    fValues.push_back(value);
}

template<>
void GamTHitAttribute<double>::FillToRoot(size_t index) {
    auto ram = G4RootAnalysisManager::Instance();
    auto v = fValues[index];
    ram->FillNtupleDColumn(fTupleId, fHitAttributeId, v);
}

template<>
void GamTHitAttribute<int>::FillToRoot(size_t index) {
    auto ram = G4RootAnalysisManager::Instance();
    auto v = fValues[index];
    ram->FillNtupleIColumn(fTupleId, fHitAttributeId, v);
}

template<>
void GamTHitAttribute<std::string>::FillToRoot(size_t index) {
    auto ram = G4RootAnalysisManager::Instance();
    auto v = fValues[index];
    ram->FillNtupleSColumn(fTupleId, fHitAttributeId, v);
}

template<>
void GamTHitAttribute<G4ThreeVector>::FillToRoot(size_t index) {
    auto ram = G4RootAnalysisManager::Instance();
    auto v = fValues[index];
    ram->FillNtupleDColumn(fTupleId, fHitAttributeId, v[0]);
    ram->FillNtupleDColumn(fTupleId, fHitAttributeId + 1, v[1]);
    ram->FillNtupleDColumn(fTupleId, fHitAttributeId + 2, v[2]);
}

template<>
std::vector<double> &GamTHitAttribute<double>::GetDValues() {
    return fValues;
}

template<>
std::vector<int> &GamTHitAttribute<int>::GetIValues() {
    return fValues;
}

template<>
std::vector<std::string> &GamTHitAttribute<std::string>::GetSValues() {
    return fValues;
}

template<>
std::vector<G4ThreeVector> &GamTHitAttribute<G4ThreeVector>::Get3Values() {
    return fValues;
}

