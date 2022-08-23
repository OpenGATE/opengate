/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#ifndef GateHitsCollectionIterator_h
#define GateHitsCollectionIterator_h

#include "G4TouchableHistory.hh"
#include "GateHitsCollection.h"
#include <cstddef>
#include <iterator>

/*
 TODO
 */

class GateHitsCollectionIterator {
public:
  GateHitsCollectionIterator();

  GateHitsCollectionIterator(GateHitsCollection *h, size_t index);

  void TrackAttribute(const std::string &name, double **value);

  void TrackAttribute(const std::string &name, G4ThreeVector **value);

  void TrackAttribute(const std::string &name,
                      GateUniqueVolumeID::Pointer **value);

  bool IsAtEnd() const;

  void GoToBegin();

  void GoTo(size_t i);

  void Reset();

  void operator++(int);

  GateHitsCollection *fHitsCollection;
  size_t fIndex;

  std::vector<double **> fDAttributes;
  std::vector<std::vector<double> *> fDAttributesVector;

  std::vector<G4ThreeVector **> f3Attributes;
  std::vector<std::vector<G4ThreeVector> *> f3AttributesVector;

  std::vector<GateUniqueVolumeID::Pointer **> fUAttributes;
  std::vector<std::vector<GateUniqueVolumeID::Pointer> *> fUAttributesVector;
};

#endif // GateHitsCollectionIterator_h
