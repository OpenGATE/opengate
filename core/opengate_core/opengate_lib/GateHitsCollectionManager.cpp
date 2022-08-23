/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#include "GateHitsCollectionManager.h"
#include "GateHelpers.h"

GateHitsCollectionManager *GateHitsCollectionManager::fInstance = nullptr;

GateHitsCollectionManager *GateHitsCollectionManager::GetInstance() {
  if (fInstance == nullptr)
    fInstance = new GateHitsCollectionManager();
  return fInstance;
}

GateHitsCollectionManager::GateHitsCollectionManager() {}

GateHitsCollection *
GateHitsCollectionManager::NewHitsCollection(std::string name) {
  auto hc = new GateHitsCollection(name);
  hc->SetTupleId(fMapOfHitsCollections.size());
  fMapOfHitsCollections[name] = hc;
  return hc;
}

GateHitsCollection *
GateHitsCollectionManager::GetHitsCollection(std::string name) {
  if (fMapOfHitsCollections.count(name) != 1) {
    std::ostringstream oss;
    oss << "Cannot find the Hits Collection named '" << name << "'. Abort.";
    Fatal(oss.str());
  }
  return fMapOfHitsCollections[name];
}

std::string GateHitsCollectionManager::DumpAllHitsCollections() {
  std::ostringstream oss;
  for (auto hc : fMapOfHitsCollections) {
    oss << hc.first << " ";
  }
  return oss.str();
}
