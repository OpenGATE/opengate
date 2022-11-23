/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#ifndef GateHitsCollectionManager_h
#define GateHitsCollectionManager_h

#include "G4TouchableHistory.hh"
#include "GateHitsCollection.h"
#include "digitizer/GateVDigiAttribute.h"
#include <pybind11/stl.h>

class GateHitsCollectionManager : public G4VHitsCollection {
public:
  static GateHitsCollectionManager *GetInstance();

  GateHitsCollection *NewHitsCollection(std::string name);

  GateHitsCollection *GetHitsCollection(std::string name);

  std::string DumpAllHitsCollections();

protected:
  GateHitsCollectionManager();

  static GateHitsCollectionManager *fInstance;

  std::map<std::string, GateHitsCollection *> fMapOfHitsCollections;
};

#endif // GateHitsCollectionManager_h
