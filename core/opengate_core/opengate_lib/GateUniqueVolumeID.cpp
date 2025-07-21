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

GateUniqueVolumeID::~GateUniqueVolumeID() {}

GateUniqueVolumeID::Pointer
GateUniqueVolumeID::New(const G4VTouchable *touchable, bool debug) {
  if (touchable == nullptr)
    return std::make_shared<GateUniqueVolumeID>();
  return std::make_shared<GateUniqueVolumeID>(touchable, debug);
}

GateUniqueVolumeID::GateUniqueVolumeID(const G4VTouchable *touchable,
                                       bool debug)
    : GateUniqueVolumeID() {
  // retrieve the tree of embedded volumes
  // See ComputeArrayID warning for explanation.
  const auto *hist = touchable->GetHistory();
  for (auto i = 0; i <= (int)hist->GetDepth(); i++) {
    int index = (int)hist->GetDepth() - i;
    auto v = GateUniqueVolumeID::VolumeDepthID();
    v.fVolumeName = touchable->GetVolume(index)->GetName();
    v.fCopyNb = touchable->GetCopyNumber(index);
    v.fDepth = i; // Start at world (depth=0), and increase
    v.fTranslation = touchable->GetTranslation(index); // copy the translation
    v.fRotation = G4RotationMatrix(
        *touchable->GetRotation(index)); // copy of the rotation
    v.fVolume = touchable->GetVolume(index);
    fVolumeDepthID.push_back(v);
    if (debug) {
      DDE(i);
      DDE(index);
      DDE(v.fVolumeName);
      DDE(v.fCopyNb);
      DDE(v.fTranslation);
    }
  }
  fArrayID = ComputeArrayID(touchable);
  fID = touchable->GetVolume()->GetName() + "-" + ArrayIDToStr(fArrayID);

  // Generate the deterministic numeric ID by hashing the unique string ID.
  fNumericID = std::hash<std::string>{}(fID);
}

uint64_t GateUniqueVolumeID::GetIdUpToDepthAsHash(int depth) const {
  // Check if the hash is already in our cache.
  auto it = fCachedIdDepthHash.find(depth);
  if (it != fCachedIdDepthHash.end()) {
    return it->second;
  }

  // If not, get the string ID (this function has its own cache).
  const std::string &s = GetIdUpToDepth(depth);

  // Compute the hash.
  uint64_t h = std::hash<std::string>{}(s);

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
  oss << fVolumeDepthID[depth].fVolumeName << "-";
  int i = 0;
  auto id = fArrayID;
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
  GateUniqueVolumeID::IDArrayType a{};
  a.fill(-1);
  int depth = (int)hist->GetDepth();
  for (auto i = 0; i <= depth; i++) {
    a[i] = touchable->GetCopyNumber(depth - i);
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

std::ostream &operator<<(std::ostream &os,
                         const GateUniqueVolumeID::VolumeDepthID &v) {
  os << v.fDepth << " " << v.fVolumeName << " " << v.fCopyNb;
  return os;
}

const std::vector<GateUniqueVolumeID::VolumeDepthID> &
GateUniqueVolumeID::GetVolumeDepthID() const {
  return fVolumeDepthID;
}

G4AffineTransform *GateUniqueVolumeID::GetWorldToLocalTransform(size_t depth) {
  auto t = GetLocalToWorldTransform(depth);
  auto translation = t->NetTranslation();
  auto rotation = t->NetRotation();
  rotation.invert();
  translation = rotation * translation;
  translation = -translation;
  auto tt = new G4AffineTransform(rotation, translation);
  delete t; // Avoid memory leak
  return tt;
}

G4AffineTransform *GateUniqueVolumeID::GetLocalToWorldTransform(size_t depth) {
  if (depth >= fVolumeDepthID.size()) {
    std::ostringstream oss;
    oss << "Error depth = " << depth << " while vol depth is "
        << fVolumeDepthID.size() << " " << fID
        << ". It can happens for example when centroid is outside a deep "
           "volume (crystal) and in";
    Fatal(oss.str());
  }
  auto &rotation = fVolumeDepthID[depth].fRotation;
  auto &translation = fVolumeDepthID[depth].fTranslation;
  auto t = new G4AffineTransform(rotation, translation);
  return t;
}
