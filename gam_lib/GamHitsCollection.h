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


class GamHitsCollection : public G4VHitsCollection {
public:

    GamHitsCollection(std::string collName);

    virtual ~GamHitsCollection();

    void StartInitialization();

    void InitializeHitAttribute(std::string name);

    void FinishInitialization();

    void Write();

    void Close();

    void SetFilename(std::string filename);

    std::string GetFilename() const { return fFilename; }

    std::string GetTitle() const { return fHitsCollectionTitle; }

    void SetTupleId(G4int id) { fTupleId = id; }

    G4int GetTupleId() const { return fTupleId; }

    const std::vector<GamVHitAttribute *> &GetHitAttributes() const { return fHitAttributes; }

    void ProcessHits(G4Step *step, G4TouchableHistory *touchable);

protected:
    std::string fFilename;
    std::string fHitsCollectionName;
    std::string fHitsCollectionTitle;
    std::map<std::string, GamVHitAttribute *> fHitAttributeMap;
    std::vector<GamVHitAttribute *> fHitAttributes;
    G4int fTupleId;

};

#endif // GamHitsCollection_h
