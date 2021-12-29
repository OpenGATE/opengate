/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#ifndef GamHitsCollectionsRootManager_h
#define GamHitsCollectionsRootManager_h

#include <pybind11/stl.h>
#include "GamVHitAttribute.h"
#include "GamHelpers.h"
#include "GamHitsCollection.h"


class GamHitsCollectionsRootManager {
    /*
     Singleton object.
     This class manages HitsCollection data as G4 root NTuples.
     Can write root files.
     - works for multi threads
     - works for multi NTuples
     - works for multi filenames
     - works for multi runs

     If there are several NTuples and one single filename,
     each tuple is a different branch.

     */
public:

    static GamHitsCollectionsRootManager *

    GetInstance();

    void OpenFile(int tupleId, std::string filename);

    void CloseFile(int tupleId);

    void Write();

    int DeclareNewTuple(std::string name);

    void CreateRootTuple(GamHitsCollection *hc);

    void CreateNtupleColumn(int tupleId, GamVHitAttribute *att);

    void AddNtupleRow(int tupleId);

protected:
    GamHitsCollectionsRootManager();

    static GamHitsCollectionsRootManager *fInstance;

    std::map<std::string, int> fTupleNameIdMap;

};

#endif // GamHitsCollectionsRootManager_h
