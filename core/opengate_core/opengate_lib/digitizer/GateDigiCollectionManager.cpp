/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#include "GateDigiCollectionManager.h"
#include "../GateHelpers.h"

GateDigiCollectionManager *GateDigiCollectionManager::fInstance = nullptr;

GateDigiCollectionManager *GateDigiCollectionManager::GetInstance() {
  if (fInstance == nullptr)
    fInstance = new GateDigiCollectionManager();
  return fInstance;
}

GateDigiCollectionManager::GateDigiCollectionManager() {}

GateDigiCollection *
GateDigiCollectionManager::NewDigiCollection(std::string name) {
  auto hc = new GateDigiCollection(name);
  hc->SetTupleId(fMapOfDigiCollections.size());
  fMapOfDigiCollections[name] = hc;
  return hc;
}

GateDigiCollection *
GateDigiCollectionManager::GetDigiCollection(std::string name) {
  if (fMapOfDigiCollections.count(name) != 1) {
    std::ostringstream oss;
    oss << "Cannot find the DigiCollection named '" << name << "'. Abort.";
    Fatal(oss.str());
  }
  return fMapOfDigiCollections[name];
}

std::string GateDigiCollectionManager::DumpAllDigiCollections() {
  std::ostringstream oss;
  for (auto hc : fMapOfDigiCollections) {
    oss << hc.first << " ";
  }
  return oss.str();
}
