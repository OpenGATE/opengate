/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#ifndef GateHitsCollectionManager_h
#define GateHitsCollectionManager_h

#include "G4TouchableHistory.hh"
#include "GateDigiCollection.h"
#include "GateVDigiAttribute.h"
#include <pybind11/stl.h>

class GateDigiCollectionManager {
public:
  static GateDigiCollectionManager *GetInstance();

  GateDigiCollection *NewDigiCollection(const std::string &name);

  GateDigiCollection *GetDigiCollection(const std::string &name);

  std::string DumpAllDigiCollections();

protected:
  GateDigiCollectionManager();

  static GateDigiCollectionManager *fInstance;

  std::map<std::string, GateDigiCollection *> fMapOfDigiCollections;
};

#endif // GateHitsCollectionManager_h
