/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#include "GateUniqueVolumeID.h"
#include "G4NavigationHistory.hh"
#include "G4VPhysicalVolume.hh"
#include "GateHelpers.h"
#include <functional> // Required for std::hash
#include <sstream>

GateUniqueVolumeID::GateUniqueVolumeID() {
  fID = "undefined";
  fNumericID = 0;
}

GateUniqueVolumeID::~GateUniqueVolumeID() = default;

GateUniqueVolumeID::Pointer
GateUniqueVolumeID::New(const G4VTouchable *touchable, bool debug) {
  if (touchable == nullptr)
    return std::make_shared<GateUniqueVolumeID>();
  return std::make_shared<GateUniqueVolumeID>(touchable, debug);
}

GateUniqueVolumeID::GateUniqueVolumeID(const G4VTouchable *touchable,
                                       bool debug)
    : GateUniqueVolumeID() {
  // Retrieve the tree of the embedded volumes
  // See ComputeArrayID warning for explanation.
  const auto *hist = touchable->GetHistory();
  fTouchable = G4NavigationHistory(*hist); // this is a copy

  if (debug) {
    for (auto i = 0; i <= (int)hist->GetDepth(); i++) {
      // FIXME
      const int index = (int)hist->GetDepth() - i;
      if (touchable->GetVolume(index) == nullptr)
        continue;
      DDE(i);
      DDE(index);
      DDE(touchable->GetVolume(index)->GetName());
      DDE(touchable->GetCopyNumber(index));
      DDE(touchable->GetTranslation(index));
    }
  }
  fArrayID = ComputeArrayID(touchable);
  fID = touchable->GetVolume()->GetName() + "-" + ArrayIDToStr(fArrayID);

  // Generate the deterministic numeric ID by hashing the unique string ID.
  fNumericID = std::hash<std::string>{}(fID);
}

uint64_t GateUniqueVolumeID::GetIdUpToDepthAsHash(const int depth) const {
  // Check if the hash is already in our cache.
  auto it = fCachedIdDepthHash.find(depth);
  if (it != fCachedIdDepthHash.end()) {
    return it->second;
  }

  // If not, get the string ID (this function has its own cache).
  const std::string &s = GetIdUpToDepth(depth);

  // Compute the hash.
  const uint64_t h = std::hash<std::string>{}(s);

  // Store the newly computed hash in our cache and return it.
  fCachedIdDepthHash[depth] = h;
  return h;
}

std::string GateUniqueVolumeID::GetIdUpToDepth(int depth) const {
  if (depth == -1)
    return fID;

  // Check if the string is already in our cache.
  auto it = fCachedIdDepth.find(depth);
  if (it != fCachedIdDepth.end()) {
    return it->second;
  }

  // If not, build the string.
  std::ostringstream oss;
  oss << fTouchable.GetVolume(depth)->GetName() << "-";
  int i = 0;
  const auto id = fArrayID;
  bool appended = false;
  while (i <= depth && id[i] != -1) {
    oss << id[i] << "_";
    appended = true;
    i++;
  }
  auto s = oss.str();
  if (appended) {
    s.pop_back();
  }

  // Store the newly created string in the cache and return it.
  fCachedIdDepth[depth] = s;
  return s;
}

GateUniqueVolumeID::IDArrayType
GateUniqueVolumeID::ComputeArrayID(const G4VTouchable *touchable) {
  /*
     WARNING. For an unknown (but probably good) reason,
     looping on the touchable->GetHistory() or looping with
     touchable->Get(depth) is not equivalent for parameterised volume. I choose
     to keep the latter as it leads to similar results between repeated or
     parametrised volumes.
   */
  const auto *hist = touchable->GetHistory();
  IDArrayType a{};
  a.fill(-1);
  const int depth = static_cast<int>(hist->GetDepth());
  int array_idx = 0;
  for (auto i = 0; i <= depth; i++) {
    const int touchable_index = depth - i;

    // Check if the volume pointer at this depth is valid.
    if (touchable->GetVolume(touchable_index) != nullptr) {
      // It's a valid level, so store its copy number in our array
      // at the current 'array_idx'.
      a[array_idx] = touchable->GetCopyNumber(touchable_index);

      // Increment the array index to the next valid level.
      array_idx++;
    }
  }
  return a;
}

std::string GateUniqueVolumeID::ArrayIDToStr(IDArrayType id) {
  std::ostringstream oss;
  size_t i = 0;
  while (i < id.size() && id[i] != -1) {
    oss << id[i] << "_";
    i++;
  }
  auto s = oss.str();
  if (!s.empty()) {
    s.pop_back();
  }
  return s;
}

G4VPhysicalVolume *GateUniqueVolumeID::GetTopPhysicalVolume() const {
  return fTouchable.GetVolume(GetDepth());
}
