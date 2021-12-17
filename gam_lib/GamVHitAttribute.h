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

    // FIXME for all types
    virtual void FillDValue(double v);

    // Name of the attribute (e.g. "KinetikEnergy")
    std::string fHitAttributeName;

    // Attribute type as a single character : D I S 3
    char fHitAttributeType;

    // Attribute index in a given HitCollection
    G4int fHitAttributeId;

    // Index of the HitCollection in the root tree
    G4int fTupleId;

    // Main function performing the process hit
    typedef std::function<void(GamVHitAttribute *b, G4Step *, G4TouchableHistory *)> ProcessHitsFunctionType;
    ProcessHitsFunctionType fProcessHitsFunction;

};

#endif // GamVHitBranch_h
