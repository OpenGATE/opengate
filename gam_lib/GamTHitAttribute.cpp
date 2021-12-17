/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#include "GamTHitAttribute.h"
#include "GamTBranch.h"
#include "GamHitsCollectionsRootManager.h"
#include "G4RunManager.hh"

template<>
GamTHitAttribute<double>::GamTHitAttribute(std::string vname) :
    GamVHitAttribute(vname, 'D') {
}

template<>
GamTHitAttribute<int>::GamTHitAttribute(std::string vname) :
    GamVHitAttribute(vname, 'I') {
}

template<>
GamTHitAttribute<std::string>::GamTHitAttribute(std::string vname) :
    GamVHitAttribute(vname, 'S') {
}

template<>
GamTHitAttribute<G4ThreeVector>::GamTHitAttribute(std::string vname) :
    GamVHitAttribute(vname, '3') {
}

