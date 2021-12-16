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
     This class manage a list of named HitAttribute. Each define one single "ProcessHit" function that consider
     a step and return a value. The value can be double, int, string, G4ThreeVector according to the type.

     Additional attributes can be added by implementing one single function "fProcessHitsFunction".


     */
public:

    static GamHitAttributeManager *GetInstance();

    void OpenFile(std::string filename);

    void CloseFile(int tupleId);

    int DeclareNewTuple(std::string name);

    //void InsertTupleId(int tupleId);

    void CreateRootTuple(std::shared_ptr<GamHitsCollection> hc);

    GamVHitAttribute *NewHitAttribute(std::string name);

    std::string DumpAvailableHitAttributeNames();

    std::map<std::string, int> fTupleNameIdMap;
    std::map<std::string, std::set<int>> fBuildForThisThreadMap;

protected:
    GamHitAttributeManager();

    static GamHitAttributeManager *fInstance;

    void InitializeAllHitAttributes();

    std::map<std::string, GamVHitAttribute *> fAvailableHitAttributes;
    std::set<int> fTupleIdSet;

    GamVHitAttribute *CopyHitAttribute(GamVHitAttribute *);

    bool fMergeFlagIsSet;

};

#endif // GamHitBranchManager_h
