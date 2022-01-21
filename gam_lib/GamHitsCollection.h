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

/*
 * Management of a Hits Collection.
 * See usage example in GamHitsCollectionActor
 *
 * - Can only be created with GamHitsCollectionManager::GetInstance()->NewHitsCollection("toto")
 *   (all HC must have a different name)
 * - Attributes must be initialized before use (in StartSimulationAction)
 *   with a list of attribute names : InitializeHitAttributes
 *
 *  - if root output:
 *    1) SetFilename
 *    2) CreateRootTupleForMaster after attributes initialisation, in StartSimulationAction
 *    3) CreateRootTupleForWorker in RunAction  !! ONLY DURING FIRST RUN !!
 *    4) FillToRoot to copy the values in the root file
 *        Either each Run, but Clear the data after to avoid filling two times the same values
 *        Either during last run.
 *    5) Write
 *       If MT, need Write for all threads (EndOfRunAction) and for Master (EndSimulationAction) *
 *    6) Close may not be needed (unsure)
 *
 */

class GamHitsCollection : public G4VHitsCollection {
public:

    friend GamHitsCollectionManager;

    ~GamHitsCollection() override;

    void InitializeHitAttributes(const std::vector<std::string> &names);

    void CreateRootTupleForMaster();

    void CreateRootTupleForWorker();

    void FillToRoot(bool clear=true);

    void Write();

    void Close();

    void SetFilename(std::string filename);

    std::string GetFilename() const { return fFilename; }

    std::string GetTitle() const { return fHitsCollectionTitle; }

    void SetTupleId(int id) { fTupleId = id; }

    int GetTupleId() const { return fTupleId; }

    virtual size_t GetSize() const override;

    void Clear();

    std::vector<GamVHitAttribute *> &GetHitAttributes() { return fHitAttributes; }

    GamVHitAttribute *GetHitAttribute(const std::string &name);

    void ProcessHits(G4Step *step, G4TouchableHistory *touchable);

protected:
    // Can only be created by GamHitsCollectionManager
    GamHitsCollection(std::string collName);

    std::string fFilename;
    std::string fHitsCollectionName;
    std::string fHitsCollectionTitle;
    std::map<std::string, GamVHitAttribute *> fHitAttributeMap;
    std::vector<GamVHitAttribute *> fHitAttributes;
    int fTupleId;
    int fCurrentHitAttributeId;

    void StartInitialization();

    void InitializeHitAttribute(std::string name);

    void FinishInitialization();

};

#endif // GamHitsCollection_h
