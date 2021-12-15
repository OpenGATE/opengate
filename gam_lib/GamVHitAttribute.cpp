/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#include "GamVHitAttribute.h"
#include "GamTBranch.h"

GamVHitAttribute::GamVHitAttribute(std::string vname, char vtype) {
    fHitAttributeName = vname;
    fHitAttributeType = vtype;
}

GamVHitAttribute::~GamVHitAttribute() {
}

void GamVHitAttribute::ProcessHits(G4Step *step, G4TouchableHistory *history) {
    //DDD("Process Hits");
    //DDD(fHitAttributeName);
    fProcessHitsFunction(this, step, history);
    //DDD("end process hits");
}

void GamVHitAttribute::FillDValue(double) {
    std::ostringstream oss;
    oss << "Internal error. FillDValue must be defined for this attribute : "
        << fHitAttributeName << " " << fHitAttributeType;
    Fatal(oss.str());
}