/* --------------------------------------------------
   Copyright (C): OpenGate Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#include "GateDigiCollection.h"
#include "G4Step.hh"
#include "GateDigiAttributeManager.h"
#include "GateDigiCollectionIterator.h"
#include "GateDigiCollectionsRootManager.h"

GateDigiCollection::GateDigiCollection(const std::string &collName)
    : G4VHitsCollection("", collName), fDigiCollectionName(collName) {
  fTupleId = -1;
  fDigiCollectionTitle = "Digi collection";
  fCurrentDigiAttributeId = 0;
  SetFilenameAndInitRoot("");
  threadLocalData.Get().fBeginOfEventIndex = 0;
  fWriteToRootFlag = false;
}

GateDigiCollection::~GateDigiCollection() = default;

size_t GateDigiCollection::GetBeginOfEventIndex() const {
  return threadLocalData.Get().fBeginOfEventIndex;
}

void GateDigiCollection::SetBeginOfEventIndex(size_t index) const {
  threadLocalData.Get().fBeginOfEventIndex = index;
}

void GateDigiCollection::SetBeginOfEventIndex() const {
  SetBeginOfEventIndex(GetSize());
}

void GateDigiCollection::SetWriteToRootFlag(const bool f) {
  fWriteToRootFlag = f;
}

void GateDigiCollection::SetFilenameAndInitRoot(const std::string &filename) {
  fFilename = filename;
  if (fFilename.empty())
    SetWriteToRootFlag(false);
  else
    SetWriteToRootFlag(true);
  RootStartInitialization();
}

void GateDigiCollection::InitDigiAttributesFromNames(
    const std::vector<std::string> &names) {
  for (const auto &name : names)
    InitDigiAttributeFromName(name);
}

void GateDigiCollection::RootStartInitialization() {
  if (!fWriteToRootFlag)
    return;
  auto *am = GateDigiCollectionsRootManager::GetInstance();
  const auto id = am->DeclareNewTuple(fDigiCollectionName);
  fTupleId = id;
}

void GateDigiCollection::RootInitializeTupleForMaster() {
  if (!fWriteToRootFlag)
    return;
  auto *am = GateDigiCollectionsRootManager::GetInstance();
  am->CreateRootTuple(this);
}

void GateDigiCollection::RootInitializeTupleForWorker() {
  if (!fWriteToRootFlag)
    return;
  // no need if not multi-thread
  if (!G4Threading::IsMultithreadedApplication())
    return;
  auto *am = GateDigiCollectionsRootManager::GetInstance();
  am->CreateRootTuple(this);
  SetBeginOfEventIndex();
}

void GateDigiCollection::FillToRootIfNeeded(bool clear) {
  /*
      Policy:
      - can write to root or not according to the flag
      - can clear every N calls
   */
  if (!fWriteToRootFlag) {
    // need to set the index before (in case we don't clear)
    if (clear)
      Clear();
    else
      SetBeginOfEventIndex();
    return;
  }
  FillToRoot();
}

void GateDigiCollection::FillToRoot() {
  /*
   * maybe not very efficient to loop that way (row then column)
   * but I don't manage to do elsewhere
   */
  auto *am = GateDigiCollectionsRootManager::GetInstance();
  for (size_t i = 0; i < GetSize(); i++) {
    for (auto *att : fDigiAttributes) {
      att->FillToRoot(i);
    }
    am->AddNtupleRow(fTupleId);
  }
  // required! Cannot fill without clearing
  Clear();
}

void GateDigiCollection::Clear() const {
  for (auto *att : fDigiAttributes) {
    att->Clear();
  }
  SetBeginOfEventIndex(0);
}

void GateDigiCollection::Write() const {
  if (!fWriteToRootFlag)
    return;
  const auto *am = GateDigiCollectionsRootManager::GetInstance();
  am->Write(fTupleId);
}

void GateDigiCollection::Close() const {
  if (!fWriteToRootFlag)
    return;
  auto *am = GateDigiCollectionsRootManager::GetInstance();
  am->CloseFile(fTupleId);
}

void GateDigiCollection::InitDigiAttributeFromName(const std::string &name) {
  // FIXME: redundant check. this is also checked in InitDigiAttribute()
  if (fDigiAttributeMap.find(name) != fDigiAttributeMap.end()) {
    std::ostringstream oss;
    oss << "Error the branch named '" << name
        << "' is already initialized. Abort";
    Fatal(oss.str());
  }
  auto *att = GateDigiAttributeManager::GetInstance()->GetDigiAttribute(name);
  InitDigiAttribute(att);
}

void GateDigiCollection::InitDigiAttribute(GateVDigiAttribute *att) {
  const auto name = att->GetDigiAttributeName();
  if (fDigiAttributeMap.find(name) != fDigiAttributeMap.end()) {
    std::ostringstream oss;
    oss << "Error the branch named '" << name
        << "' is already initialized. Abort";
    Fatal(oss.str());
  }
  fDigiAttributes.push_back(att);
  fDigiAttributeMap[name] = att;
  att->SetDigiAttributeId(fCurrentDigiAttributeId);
  att->SetTupleId(fTupleId);
  fCurrentDigiAttributeId++;
  // special case for type=3
  if (att->GetDigiAttributeType() == '3')
    fCurrentDigiAttributeId += 2;
}

void GateDigiCollection::InitDigiAttributesFromCopy(
    GateDigiCollection *input,
    const std::vector<std::string> &skipDigiAttributeNames) {
  auto *dgm = GateDigiAttributeManager::GetInstance();
  for (const auto &att : input->GetDigiAttributes()) {
    auto name = att->GetDigiAttributeName();
    // Skip this attributes ?
    if (std::find(skipDigiAttributeNames.begin(), skipDigiAttributeNames.end(),
                  name) != skipDigiAttributeNames.end())
      continue;
    // Copy it
    auto *copy = dgm->CopyDigiAttribute(att);
    InitDigiAttribute(copy);
  }
}

void GateDigiCollection::FillHits(G4Step *step) {
  for (auto *att : fDigiAttributes) {
    att->ProcessHits(step);
  }
}

void GateDigiCollection::FillDigiWithEmptyValue() {
  for (auto *att : fDigiAttributes) {
    att->FillDigiWithEmptyValue();
  }
}

size_t GateDigiCollection::GetSize() const {
  if (fDigiAttributes.empty())
    return 0;
  return fDigiAttributes[0]->GetSize();
}

GateVDigiAttribute *
GateDigiCollection::GetDigiAttribute(const std::string &name) {
  // Sometimes it is faster to apologize instead of asking permission ...
  try {
    return fDigiAttributeMap.at(name);
  } catch (std::out_of_range &) {
    std::ostringstream oss;
    oss << "Error the branch named '" << name << "' does not exist. Abort";
    Fatal(oss.str());
  }
  return nullptr; // fake to avoid warning
}

bool GateDigiCollection::IsDigiAttributeExists(const std::string &name) const {
  return (fDigiAttributeMap.count(name) != 0);
}

std::set<std::string> GateDigiCollection::GetDigiAttributeNames() const {
  std::set<std::string> list;
  for (auto *att : fDigiAttributes)
    list.insert(att->GetDigiAttributeName());
  return list;
}

GateDigiCollection::Iterator GateDigiCollection::NewIterator() {
  return {this, 0};
}

std::string GateDigiCollection::DumpLastDigi() const {
  if (GetSize() == 0)
    return "";
  auto n = GetSize() - 1;
  return DumpDigi(n);
}

std::string GateDigiCollection::DumpDigi(int i) const {
  if (GetSize() == 0)
    return "";
  std::ostringstream oss;
  for (auto *att : fDigiAttributes) {
    oss << att->GetDigiAttributeName() << " = " << att->Dump(i) << "  ";
  }
  return oss.str();
}
