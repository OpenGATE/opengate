/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#include "GateHitsCollectionsRootManager.h"
#include "G4RootAnalysisManager.hh"
#include "G4Run.hh"
#include "G4RunManager.hh"

GateHitsCollectionsRootManager *GateHitsCollectionsRootManager::fInstance =
    nullptr;

GateHitsCollectionsRootManager *GateHitsCollectionsRootManager::GetInstance() {
  if (fInstance == nullptr)
    fInstance = new GateHitsCollectionsRootManager();
  return fInstance;
}

GateHitsCollectionsRootManager::GateHitsCollectionsRootManager() {}

void GateHitsCollectionsRootManager::OpenFile(int tupleId,
                                              std::string filename) {
  // Warning : this pointer is not the same for all workers in MT mode
  auto *ram = G4RootAnalysisManager::Instance();
  if (not ram->IsOpenFile()) {
    // The following does not seems to work (default is 4000)
    // ram->SetBasketEntries(8000);
    // ram->SetBasketSize(5e6);

    // SetNtupleMerging must be called before OpenFile
    // To avoid a warning, the flag is only set for the master thread
    // and for the first opened tuple only.
    if (G4Threading::IsMultithreadedApplication()) {
      auto *run = G4RunManager::GetRunManager()->GetCurrentRun();
      if (run) {
        if (run->GetRunID() == 0 and tupleId == 0)
          ram->SetNtupleMerging(true);
      } else
        ram->SetNtupleMerging(true);
    }
    ram->OpenFile(filename);
  }
}

int GateHitsCollectionsRootManager::DeclareNewTuple(std::string name) {
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
      DDD("tuple already declared");
      DDD(m.second);
      DDD(name)
      Fatal("Error in GateHitsCollectionsRootManager::DeclareNewTuple");
      return m.second;
    }
    id = std::max(id, m.second);
  }
  id += 1;
  fTupleNameIdMap[name] = id;
  fTupleShouldBeWritten[id] = false;
  return id;
}

void GateHitsCollectionsRootManager::AddNtupleRow(int tupleId) {
  auto *ram = G4RootAnalysisManager::Instance();
  ram->AddNtupleRow(tupleId);
}

void GateHitsCollectionsRootManager::Write(int tupleId) {
  auto &tl = threadLocalData.Get();
  // Do nothing if already Write
  if (G4Threading::IsMasterThread() and tl.fFileHasBeenWrittenByMaster)
    return;
  if (not G4Threading::IsMasterThread() and tl.fFileHasBeenWrittenByWorker)
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
    if (not G4Threading::IsMasterThread())
      tl.fFileHasBeenWrittenByWorker = true;
  }
}

void GateHitsCollectionsRootManager::CreateRootTuple(GateHitsCollection *hc) {
  auto *ram = G4RootAnalysisManager::Instance();

  // check filename
  if (hc->GetFilename().empty()) {
    std::ostringstream oss;
    oss << "Filename for the HitsCollection '" << hc->GetName()
        << "' is empty. Use SetFilename. Abort.";
    Fatal(oss.str());
  }

  // check attributes
  if (hc->GetHitAttributes().empty()) {
    std::ostringstream oss;
    oss << "The HitsCollection '" << hc->GetName()
        << "' has no attributes. Use InitializeHitAttributes. Abort.";
    Fatal(oss.str());
  }

  // Later, the verbosity could be an option
  ram->SetVerboseLevel(0);
  OpenFile(hc->GetTupleId(), hc->GetFilename());
  auto id = ram->CreateNtuple(hc->GetName(), hc->GetTitle());

  // Important ! This allows to write to several root files
  ram->SetNtupleFileName(hc->GetTupleId(), hc->GetFilename());
  for (auto *att : hc->GetHitAttributes()) {
    // (depends on the type -> todo in the HitAttribute ?)
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

void GateHitsCollectionsRootManager::CreateNtupleColumn(
    int tupleId, GateVDigiAttribute *att) {
  auto *ram = G4RootAnalysisManager::Instance();
  int att_id = -1;
  if (att->GetDigiAttributeType() == 'D')
    att_id = ram->CreateNtupleDColumn(tupleId, att->GetDigiAttributeName());
  if (att->GetDigiAttributeType() == 'S')
    att_id = ram->CreateNtupleSColumn(tupleId, att->GetDigiAttributeName());
  if (att->GetDigiAttributeType() == 'I')
    att_id = ram->CreateNtupleIColumn(tupleId, att->GetDigiAttributeName());
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
    DDD(att->GetDigiAttributeName());
    DDD(att->GetDigiAttributeType());
    DDD(att->GetDigiAttributeTupleId());
    Fatal("Error GateHitsCollectionsRootManager::CreateNtupleColumn");
  }
  att->SetDigiAttributeId(att_id);
}

void GateHitsCollectionsRootManager::CloseFile(int tupleId) {
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
