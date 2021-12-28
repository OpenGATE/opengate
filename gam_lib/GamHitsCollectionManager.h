/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#ifndef GamHitsCollectionManager_h
#define GamHitsCollectionManager_h

#include <pybind11/stl.h>
#include "G4TouchableHistory.hh"
#include "GamVHitAttribute.h"
#include "GamHitsCollection.h"


class GamHitsCollectionManager : public G4VHitsCollection {
public:

    static GamHitsCollectionManager *GetInstance();

    GamHitsCollection *NewHitsCollection(std::string name);

    GamHitsCollection *GetHitsCollection(std::string name);

protected:
    GamHitsCollectionManager();

    static GamHitsCollectionManager *fInstance;

    std::map<std::string, GamHitsCollection *> fMapOfHC;

};

#endif // GamHitsCollectionManager_h
