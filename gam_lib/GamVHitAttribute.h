/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#ifndef GamVHitAttribute_h
#define GamVHitAttribute_h

#include <pybind11/stl.h>
#include "GamHelpers.h"
#include "G4TouchableHistory.hh"

class GamVHitAttribute {
public:
    GamVHitAttribute(std::string vname, char vtype);

    virtual ~GamVHitAttribute();

    void ProcessHits(G4Step *step, G4TouchableHistory *touchable);

    virtual std::vector<double> &GetDValues();

    virtual std::vector<int> &GetIValues();

    virtual std::vector<std::string> &GetSValues();

    virtual std::vector<G4ThreeVector> &Get3Values();

    virtual void FillToRoot(size_t) const {}

    virtual void FillDValue(double) {}

    virtual void FillSValue(std::string) {}

    virtual void FillIValue(int) {}

    virtual void Fill3Value(G4ThreeVector) {}

    virtual int GetSize() const = 0;

    virtual void Clear() = 0;

    void SetHitAttributeId(int id) { fHitAttributeId = id; }

    void SetTupleId(int id) { fTupleId = id; }

    std::string GetHitAttributeName() const { return fHitAttributeName; }

    char GetHitAttributeType() const { return fHitAttributeType; }

    int GetHitAttributeId() const { return fHitAttributeId; }

    int GetHitAttributeTupleId() const { return fTupleId; }

    // Main function performing the process hit
    typedef std::function<void(GamVHitAttribute *b, G4Step *, G4TouchableHistory *)> ProcessHitsFunctionType;
    ProcessHitsFunctionType fProcessHitsFunction;

protected:

    // Name of the attribute (e.g. "KineticEnergy")
    std::string fHitAttributeName;

    // Attribute type as a single character : D I S 3
    char fHitAttributeType;

    // Attribute index in a given HitCollection
    G4int fHitAttributeId;

    // Index of the HitCollection in the root tree
    G4int fTupleId;

};

#endif // GamVHitAttribute_h
