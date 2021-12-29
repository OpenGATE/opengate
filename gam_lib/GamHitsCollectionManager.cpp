/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#include "GamHitsCollectionManager.h"
#include "GamHelpers.h"

GamHitsCollectionManager *GamHitsCollectionManager::fInstance = nullptr;

GamHitsCollectionManager *GamHitsCollectionManager::GetInstance() {
    if (fInstance == nullptr) fInstance = new GamHitsCollectionManager();
    return fInstance;
}

GamHitsCollectionManager::GamHitsCollectionManager() {

}

GamHitsCollection *GamHitsCollectionManager::NewHitsCollection(std::string name) {
    auto hc = new GamHitsCollection(name);
    hc->SetTupleId(fMapOfHitsCollections.size());
    fMapOfHitsCollections[name] = hc;
    return hc;
}

GamHitsCollection *GamHitsCollectionManager::GetHitsCollection(std::string name) {
    if (fMapOfHitsCollections.count(name) != 1) {
        std::ostringstream oss;
        oss << "Cannot find the Hits Collection named '" << name
            << "'. Abort.";
        Fatal(oss.str());
    }
    return fMapOfHitsCollections[name];
}
