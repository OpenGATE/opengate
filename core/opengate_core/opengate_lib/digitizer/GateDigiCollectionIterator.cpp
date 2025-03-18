/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#include "GateDigiCollectionIterator.h"
#include "GateDigiCollection.h"

GateDigiCollectionIterator::GateDigiCollectionIterator(GateDigiCollection *h,
                                                       size_t index) {
  fDigiCollection = h;
  fIndex = index;
}

GateDigiCollectionIterator::GateDigiCollectionIterator() { fIndex = 0; }

void GateDigiCollectionIterator::TrackAttribute(const std::string &name,
                                                double **value) {
  auto *att = fDigiCollection->GetDigiAttribute(name);
  auto &v = att->GetDValues();
  fDAttributes.push_back(value);
  fDAttributesVector.push_back(&v);
}

void GateDigiCollectionIterator::TrackAttribute(const std::string &name,
                                                G4ThreeVector **value) {
  auto *att = fDigiCollection->GetDigiAttribute(name);
  auto &v = att->Get3Values();
  f3Attributes.push_back(value);
  f3AttributesVector.push_back(&v);
}

void GateDigiCollectionIterator::TrackAttribute(
    const std::string &name, GateUniqueVolumeID::Pointer **value) {
  auto *att = fDigiCollection->GetDigiAttribute(name);
  auto &v = att->GetUValues();
  fUAttributes.push_back(value);
  fUAttributesVector.push_back(&v);
}

void GateDigiCollectionIterator::operator++(int) {
  fIndex++;
  GoTo(fIndex);
}

void GateDigiCollectionIterator::GoTo(size_t index) {
  // (note: I tried to inline the function, it does not really change the speed)
  for (size_t i = 0; i < fDAttributes.size(); i++) {
    auto &v = *fDAttributesVector[i];
    *fDAttributes[i] = &v[index];
  }
  for (size_t i = 0; i < f3Attributes.size(); i++) {
    auto &v = *f3AttributesVector[i];
    *f3Attributes[i] = &v[index];
  }
  for (size_t i = 0; i < fUAttributes.size(); i++) {
    auto &v = *fUAttributesVector[i];
    *fUAttributes[i] = &v[index];
  }
}

bool GateDigiCollectionIterator::IsAtEnd() const {
  return (fIndex >= fDigiCollection->GetSize());
}

void GateDigiCollectionIterator::GoToBegin() {
  fIndex = fDigiCollection->GetBeginOfEventIndex();
  GoTo(fIndex);
}

void GateDigiCollectionIterator::Reset() {
  fIndex = 0;
  GoToBegin();
}
