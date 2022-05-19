/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#ifndef GamHitsCollectionIterator_h
#define GamHitsCollectionIterator_h

#include <iterator>
#include <cstddef>
#include "G4TouchableHistory.hh"
#include "GamHitsCollection.h"

/*
 TODO
 */

class GamHitsCollectionIterator {
public:

    GamHitsCollectionIterator();

    GamHitsCollectionIterator(GamHitsCollection *h, size_t index);

    void TrackAttribute(const std::string &name, double **value);

    void TrackAttribute(const std::string &name, G4ThreeVector **value);

    void TrackAttribute(const std::string &name, GamUniqueVolumeID::Pointer **value);

    bool IsAtEnd() const;

    void GoToBegin();

    void GoTo(size_t i);

    void Reset();

    void operator++(int);

    GamHitsCollection *fHitsCollection;
    size_t fIndex;

    std::vector<double **> fDAttributes;
    std::vector<std::vector<double> *> fDAttributesVector;

    std::vector<G4ThreeVector **> f3Attributes;
    std::vector<std::vector<G4ThreeVector> *> f3AttributesVector;

    std::vector<GamUniqueVolumeID::Pointer **> fUAttributes;
    std::vector<std::vector<GamUniqueVolumeID::Pointer> *> fUAttributesVector;

};


#endif // GamHitsCollectionIterator_h
