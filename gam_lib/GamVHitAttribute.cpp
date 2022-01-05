/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#include "GamVHitAttribute.h"

GamVHitAttribute::GamVHitAttribute(std::string vname, char vtype) {
    fHitAttributeName = vname;
    fHitAttributeType = vtype;
}

GamVHitAttribute::~GamVHitAttribute() {
}

void GamVHitAttribute::ProcessHits(G4Step *step, G4TouchableHistory *history) {
    fProcessHitsFunction(this, step, history);
}

std::vector<double> &GamVHitAttribute::GetDValues() {
    Fatal("Must never be there ! GamVHitAttribute D");
    static std::vector<double> fake;
    return fake; // to avoid warning
}

std::vector<int> &GamVHitAttribute::GetIValues() {
    Fatal("Must never be there ! GamVHitAttribute I");
    static std::vector<int> fake;
    return fake; // to avoid warning
}

std::vector<std::string> &GamVHitAttribute::GetSValues() {
    Fatal("Must never be there ! GamVHitAttribute S");
    static std::vector<std::string> fake;
    return fake; // to avoid warning
}

std::vector<G4ThreeVector> &GamVHitAttribute::Get3Values() {
    Fatal("Must never be there ! GamVHitAttribute 3");
    static std::vector<G4ThreeVector> fake;
    return fake; // to avoid warning
}
