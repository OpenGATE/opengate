/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#include <array>

#include "G4NavigationHistory.hh"
#include "G4RunManager.hh"
#include "G4VPhysicalVolume.hh"
#include "GateHelpers.h"
#include "GateUniqueVolumeID.h"

GateUniqueVolumeID::GateUniqueVolumeID() { fID = "undefined"; }

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
  fID = ArrayIDToStr(fArrayID);
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
  s.pop_back();
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

std::string GateUniqueVolumeID::GetIdUpToDepth(int depth) {
  if (depth == -1)
    return fID;
  if (fCachedIdDepth.count(depth) != 0) {
    return fCachedIdDepth[depth];
  }
  std::ostringstream oss;
  int i = 0;
  auto id = fArrayID;
  while (i <= depth && id[i] != -1) {
    oss << id[i] << "_";
    i++;
  }
  auto s = oss.str();
  s.pop_back();
  fCachedIdDepth[depth] = s;
  return s;
}
