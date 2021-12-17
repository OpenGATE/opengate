/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#ifndef GamHitBranchManager_h
#define GamHitBranchManager_h

#include <pybind11/stl.h>
#include "GamVHitAttribute.h"
#include "GamHelpers.h"
#include "GamHitsCollection.h"


class GamHitAttributeManager {
    /*
     Singleton object.

     This class manage the list of available Attributes

     // FIXME to split in 2 classes

     This class manages output to root files. Ideally:
     - works for Multi Threads
     - works for multi NTuples
     - works for multi filenames
     - works for multi runs
     */
public:

    static GamHitAttributeManager *GetInstance();

    void OpenFile(int tupleId, std::string filename);

    void CloseFile(int tupleId);

    void Write();

    int DeclareNewTuple(std::string name);

    void CreateRootTuple(std::shared_ptr<GamHitsCollection> hc);

    void AddNtupleRow(int tupleId);

    GamVHitAttribute *NewHitAttribute(std::string name);

    std::string DumpAvailableHitAttributeNames();

protected:
    GamHitAttributeManager();

    static GamHitAttributeManager *fInstance;

    void InitializeAllHitAttributes();

    std::map<std::string, GamVHitAttribute *> fAvailableHitAttributes;
    std::map<std::string, int> fTupleNameIdMap;
    GamVHitAttribute *CopyHitAttribute(GamVHitAttribute *);

};

#endif // GamHitBranchManager_h
