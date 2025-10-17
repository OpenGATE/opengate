/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#ifndef GateDigiCollectionsRootManager_h
#define GateDigiCollectionsRootManager_h

#include "../GateHelpers.h"
#include "GateDigiCollection.h"
#include "GateVDigiAttribute.h"
#include <pybind11/stl.h>

class GateDigiCollectionsRootManager {
  /*
   Singleton object.
   This class manages DigiCollection data as G4 root NTuples.
   Can write root files.
   - works for multi threads
   - works for multi NTuples
   - works for multi filenames
   - works for multi runs

   If there are several NTuples and one single filename,
   each tuple is in a different branch.

   */
public:
  static GateDigiCollectionsRootManager *

  GetInstance();

  void OpenFile(int tupleId, const std::string &filename);

  void CloseFile(int tupleId);

  void Write(int tupleId) const;

  int DeclareNewTuple(const std::string &name);

  void CreateRootTuple(GateDigiCollection *hc);

  void CreateNtupleColumn(int tupleId, GateVDigiAttribute *att);

  void AddNtupleRow(int tupleId);

protected:
  GateDigiCollectionsRootManager();

  static GateDigiCollectionsRootManager *fInstance;

  struct threadLocal_t {
    // std::map<std::string, int> fTupleNameIdMap;
    //  This is required to manage the Write process :
    //  only one is mandatory for all DigiCollections.
    std::map<int, bool> fTupleShouldBeWritten;
    bool fFileHasBeenWrittenByWorker;
    bool fFileHasBeenWrittenByMaster;
  };
  G4Cache<threadLocal_t> threadLocalData;

  std::map<std::string, int> fTupleNameIdMap;
  // std::map<int, bool> fAlreadyWrite;
};

#endif // GateDigiCollectionsRootManager_h
