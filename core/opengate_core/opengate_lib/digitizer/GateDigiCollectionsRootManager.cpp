/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#include "GateDigiCollectionsRootManager.h"
#include "G4RootAnalysisManager.hh"
#include "G4Run.hh"
#include "G4RunManager.hh"

GateDigiCollectionsRootManager *GateDigiCollectionsRootManager::fInstance =
    nullptr;

GateDigiCollectionsRootManager *GateDigiCollectionsRootManager::GetInstance() {
  if (fInstance == nullptr)
    fInstance = new GateDigiCollectionsRootManager();
  return fInstance;
}

GateDigiCollectionsRootManager::GateDigiCollectionsRootManager() {}

void GateDigiCollectionsRootManager::OpenFile(const int tupleId,
                                              const std::string &filename) {
  // Warning: this pointer is different for all workers in MT mode
  auto *ram = G4RootAnalysisManager::Instance();
  if (!ram->IsOpenFile()) {
    // The following does not seem to work (default is 4000)
    // ram->SetBasketEntries(8000);
    // ram->SetBasketSize(5e6);

    // SetNtupleMerging must be called before OpenFile
    // To avoid a warning, the flag is only set for the master thread
    // and for the first opened tuple only.
    if (G4Threading::IsMultithreadedApplication()) {
      auto *run = G4RunManager::GetRunManager()->GetCurrentRun();
      if (run) {
        if (run->GetRunID() == 0 && tupleId == 0)
          ram->SetNtupleMerging(true);
      } else
        ram->SetNtupleMerging(true);
    }
    ram->OpenFile(filename);
  }
}

int GateDigiCollectionsRootManager::DeclareNewTuple(const std::string &name) {
  auto &fTupleShouldBeWritten = threadLocalData.Get().fTupleShouldBeWritten;
  if (fTupleNameIdMap.count(name) != 0) {
    std::ostringstream oss;
    oss << "Error cannot create a tuple named '" << name
        << "' because it already exists. ";
    Fatal(oss.str());
  }
  int id = -1;
  for (const auto &m : fTupleNameIdMap) {
    if (m.first == name) {
      DDE("tuple already declared");
      DDE(m.second);
      DDE(name)
      Fatal("Error in GateDigiCollectionsRootManager::DeclareNewTuple");
      return m.second;
    }
    id = std::max(id, m.second);
  }
  id += 1;
  fTupleNameIdMap[name] = id;
  fTupleShouldBeWritten[id] = false;
  return id;
}

void GateDigiCollectionsRootManager::AddNtupleRow(const int tupleId) {
  auto *ram = G4RootAnalysisManager::Instance();
  ram->AddNtupleRow(tupleId);
}

void GateDigiCollectionsRootManager::Write(const int tupleId) const {
  auto &tl = threadLocalData.Get();
  // Do nothing if already Write
  if (G4Threading::IsMasterThread() && tl.fFileHasBeenWrittenByMaster)
    return;
  if (!G4Threading::IsMasterThread() && tl.fFileHasBeenWrittenByWorker)
    return;
  auto &tupleShouldBeWritten = tl.fTupleShouldBeWritten;
  tupleShouldBeWritten[tupleId] = true;
  bool shouldWrite = true;
  for (auto &m : tupleShouldBeWritten)
    if (!m.second)
      shouldWrite = false;
  if (shouldWrite) {
    auto *ram = G4RootAnalysisManager::Instance();
    ram->Write();
    // reset flags (not sure needed)
    for (auto &m : tupleShouldBeWritten)
      m.second = false;
    // Set already written flag
    if (G4Threading::IsMasterThread())
      tl.fFileHasBeenWrittenByMaster = true;
    if (!G4Threading::IsMasterThread())
      tl.fFileHasBeenWrittenByWorker = true;
  }
}

void GateDigiCollectionsRootManager::CreateRootTuple(GateDigiCollection *hc) {
  auto *ram = G4RootAnalysisManager::Instance();

  // check filename
  if (hc->GetFilename().empty()) {
    std::ostringstream oss;
    oss << "Filename for the DigiCollection '" << hc->GetName()
        << "' is empty. Use SetFilenameAndInitRoot. Abort.";
    Fatal(oss.str());
  }

  // check attributes
  if (hc->GetDigiAttributes().empty()) {
    std::ostringstream oss;
    oss << "The DigiCollection '" << hc->GetName()
        << "' has no attributes. Use InitDigiAttributesFromNames. Abort.";
    Fatal(oss.str());
  }

  // Later, the verbosity could be an option
  ram->SetVerboseLevel(0);
  OpenFile(hc->GetTupleId(), hc->GetFilename());
  auto id = ram->CreateNtuple(hc->GetName(), hc->GetTitle());

  // Important ! This allows to write to several root files
  ram->SetNtupleFileName(hc->GetTupleId(), hc->GetFilename());
  for (auto *att : hc->GetDigiAttributes()) {
    // (depends on the type -> todo in the DigiAttribute ?)
    // WARNING: the id can be different from tupleId in HC and in att
    // because it is created at all runs (mandatory).
    // So id must be used to create columns, not tupleID in att.
    CreateNtupleColumn(id, att);
  }
  ram->FinishNtuple(id);

  // Need to initialize the map for all threads
  auto &fAlreadyWriteThread = threadLocalData.Get().fTupleShouldBeWritten;
  fAlreadyWriteThread[hc->GetTupleId()] = false;
  auto &tl = threadLocalData.Get();
  tl.fFileHasBeenWrittenByWorker = false;
  tl.fFileHasBeenWrittenByMaster = false;
}

void GateDigiCollectionsRootManager::CreateNtupleColumn(
    int tupleId, GateVDigiAttribute *att) {
  auto *ram = G4RootAnalysisManager::Instance();
  int att_id = -1;
  if (att->GetDigiAttributeType() == 'D')
    att_id = ram->CreateNtupleDColumn(tupleId, att->GetDigiAttributeName());
  if (att->GetDigiAttributeType() == 'S')
    att_id = ram->CreateNtupleSColumn(tupleId, att->GetDigiAttributeName());
  if (att->GetDigiAttributeType() == 'I')
    att_id = ram->CreateNtupleIColumn(tupleId, att->GetDigiAttributeName());
  if (att->GetDigiAttributeType() == 'L') {
    Fatal("Error GateDigiCollectionsRootManager::CreateNtupleColumn no LONG "
          "possible yet");
    // att_id = ram->CreateNtupleDColumn(tupleId, att->GetDigiAttributeName());
  }
  if (att->GetDigiAttributeType() == '3') {
    att_id =
        ram->CreateNtupleDColumn(tupleId, att->GetDigiAttributeName() + "_X");
    ram->CreateNtupleDColumn(tupleId, att->GetDigiAttributeName() + "_Y");
    ram->CreateNtupleDColumn(tupleId, att->GetDigiAttributeName() + "_Z");
  }
  if (att->GetDigiAttributeType() == 'U') {
    att_id = ram->CreateNtupleSColumn(tupleId, att->GetDigiAttributeName());
  }

  if (att_id == -1) {
    DDE(att->GetDigiAttributeName());
    DDE(att->GetDigiAttributeType());
    DDE(att->GetDigiAttributeTupleId());
    Fatal("Error GateDigiCollectionsRootManager::CreateNtupleColumn");
  }
  att->SetDigiAttributeId(att_id);
}

void GateDigiCollectionsRootManager::CloseFile(int tupleId) {
  // find the tuple and remove it from the map
  for (auto iter = fTupleNameIdMap.begin(); iter != fTupleNameIdMap.end();) {
    if (iter->second == tupleId) {
      fTupleNameIdMap.erase(iter++);
    } else
      ++iter;
  }
  // close only when the last tuple is done
  if (fTupleNameIdMap.empty()) {
    auto *ram = G4RootAnalysisManager::Instance();
    ram->CloseFile();
  }
}
