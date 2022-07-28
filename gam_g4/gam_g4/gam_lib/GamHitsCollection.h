/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#ifndef GamHitsCollection_h
#define GamHitsCollection_h

#include <pybind11/stl.h>
#include "G4TouchableHistory.hh"
#include "GamVHitAttribute.h"

class GamHitsCollectionManager;

class GamHitsCollectionIterator;

/*
 * Management of a Hits Collection.
 * See usage example in GamHitsCollectionActor
 *
 * - Can only be created with GamHitsCollectionManager::GetInstance()->NewHitsCollection("toto")
 *   (all HC must have a different name) because of root management
 * - Attributes must be initialized before use (in StartSimulationAction)
 *   with a list of attribute names : InitializeHitAttributes
 *
 *  - if root output:
 *    1) SetFilename
 *    2) InitializeRootTupleForMaster after attributes initialisation, in StartSimulationAction
 *    3) InitializeRootTupleForWorker in RunAction  !! ONLY DURING FIRST RUN !!
 *    4) FillToRoot to copy the values in the root file
 *        Can be, for example each Event or each Run
 *        Clear is needed once FillToRootIfNeeded.
 *        This function also set the internal event index (needed).
 *    5) Write
 *       If MT, need Write for all threads (EndOfRunAction) and for Master (EndSimulationAction) *
 *    6) Close may not be needed (unsure)
 *
 */

class GamHitsCollection : public G4VHitsCollection {
public:

    friend GamHitsCollectionManager;

    typedef GamHitsCollectionIterator Iterator;

    ~GamHitsCollection() override;

    void InitializeHitAttributes(const std::vector<std::string> &names);

    void InitializeHitAttributes(const std::set<std::string> &names);

    void StartInitialization();

    void InitializeHitAttribute(GamVHitAttribute* att);

    void InitializeHitAttribute(const std::string &name);

    void FinishInitialization();

    void InitializeRootTupleForMaster();

    void InitializeRootTupleForWorker();

    void FillToRootIfNeeded(bool clear);

    void Write() const;

    void Close() const;

    void SetWriteToRootFlag(bool f);

    void SetFilename(std::string filename);

    std::string GetFilename() const { return fFilename; }

    std::string GetTitle() const { return fHitsCollectionTitle; }

    void SetTupleId(int id) { fTupleId = id; }

    int GetTupleId() const { return fTupleId; }

    size_t GetSize() const override;

    void Clear();

    std::vector<GamVHitAttribute *> &GetHitAttributes() { return fHitAttributes; }

    std::set<std::string> GetHitAttributeNames() const;

    GamVHitAttribute *GetHitAttribute(const std::string &name);

    bool IsHitAttributeExists(const std::string &name) const;

    void FillHits(G4Step *step);

    void FillHitsWithEmptyValue();

    std::string DumpLastHit() const;

    Iterator NewIterator();

    size_t GetBeginOfEventIndex() const;

    void SetBeginOfEventIndex(size_t index);

    void SetBeginOfEventIndex();

protected:
    // Can only be created by GamHitsCollectionManager
    explicit GamHitsCollection(const std::string &collName);

    std::string fFilename;
    std::string fHitsCollectionName;
    std::string fHitsCollectionTitle;
    std::map<std::string, GamVHitAttribute *> fHitAttributeMap;
    std::vector<GamVHitAttribute *> fHitAttributes;
    int fTupleId;
    int fCurrentHitAttributeId;
    bool fWriteToRootFlag;

    // thread local: the index of the beginning
    // of event is specific for each thread
    struct threadLocal_t {
        size_t fBeginOfEventIndex=0;
    };
    G4Cache<threadLocal_t> threadLocalData;

    void FillToRoot();

};

#endif // GamHitsCollection_h
