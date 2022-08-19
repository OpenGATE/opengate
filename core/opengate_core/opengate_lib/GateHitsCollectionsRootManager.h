/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#ifndef GateHitsCollectionsRootManager_h
#define GateHitsCollectionsRootManager_h

#include <pybind11/stl.h>
#include "GateVHitAttribute.h"
#include "GateHelpers.h"
#include "GateHitsCollection.h"


class GateHitsCollectionsRootManager {
    /*
     Singleton object.
     This class manages HitsCollection data as G4 root NTuples.
     Can write root files.
     - works for multi threads
     - works for multi NTuples
     - works for multi filenames
     - works for multi runs

     If there are several NTuples and one single filename,
     each tuple is in a different branch.

     */
public:

    static GateHitsCollectionsRootManager *

    GetInstance();

    void OpenFile(int tupleId, std::string filename);

    void CloseFile(int tupleId);

    void Write(int tupleId);

    int DeclareNewTuple(std::string name);

    void CreateRootTuple(GateHitsCollection *hc);

    void CreateNtupleColumn(int tupleId, GateVHitAttribute *att);

    void AddNtupleRow(int tupleId);

protected:
    GateHitsCollectionsRootManager();

    static GateHitsCollectionsRootManager *fInstance;

    struct threadLocal_t {
        //std::map<std::string, int> fTupleNameIdMap;
        // This is required to manage the Write process :
        // only one is mandatory for all HitsCollections.
        std::map<int, bool> fTupleShouldBeWritten;
        bool fFileHasBeenWrittenByWorker;
        bool fFileHasBeenWrittenByMaster;
    };
    G4Cache<threadLocal_t> threadLocalData;

    std::map<std::string, int> fTupleNameIdMap;
    //std::map<int, bool> fAlreadyWrite;

};

#endif // GateHitsCollectionsRootManager_h
