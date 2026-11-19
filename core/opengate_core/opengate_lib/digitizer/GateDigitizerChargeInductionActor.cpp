/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#include "GateDigitizerChargeInductionActor.h"
#include "../GateHelpers.h"
#include "../GateHelpersDict.h"
#include "GateTDigiAttribute.h"
#include <cmath>
#include <cstring>
#include <sstream>

G4Mutex ChargeInductionIgnoredHitsMutex = G4MUTEX_INITIALIZER;

GateDigitizerChargeInductionActor::GateDigitizerChargeInductionActor(
    py::dict &user_info)
    : GateVDigitizerWithOutputActor(user_info, true) {
  fActions.insert("EndOfEventAction");
  fCathodeIsPlusZ = true;
  fNeighbours = 1;
  fGain = 1.0;
  fThreshold = 0.0;
  fMiddlePositionFlag = false;
  fCrystalDepth = -1;
  fPixelDepth = -1;
  fThickness = 0;
  fWeightsAreUsedFlag = false;
  fAddPostPositionLocal = false;
  fIgnoredHitsCount = 0;
}

GateDigitizerChargeInductionActor::~GateDigitizerChargeInductionActor() =
    default;

void GateDigitizerChargeInductionActor::InitializeUserInfo(
    py::dict &user_info) {
  GateVDigitizerWithOutputActor::InitializeUserInfo(user_info);
  const auto side = DictGetStr(user_info, "cathode_side");
  if (side == "+z")
    fCathodeIsPlusZ = true;
  else if (side == "-z")
    fCathodeIsPlusZ = false;
  else
    Fatal("Error in GateDigitizerChargeInductionActor: cathode_side must be "
          "'+z' or '-z', while it is '" +
          side + "'");
  fNeighbours = DictGetInt(user_info, "neighbours");
  fGain = DictGetDouble(user_info, "gain");
  fThreshold = DictGetDouble(user_info, "signal_threshold");
  const auto hp = DictGetStr(user_info, "hit_position");
  fMiddlePositionFlag = hp == "middle";
  fAttributePolicies.InitializeUserInfo(user_info,
                                        "GateDigitizerChargeInductionActor");
}

void GateDigitizerChargeInductionActor::SetGrid(
    const std::vector<double> &pixel_size,
    const std::vector<int> &number_of_pixels,
    const std::vector<double> &center) {
  if (pixel_size.size() != 2 || number_of_pixels.size() != 2 ||
      center.size() != 2)
    Fatal("Error in GateDigitizerChargeInductionActor: pixel_size, "
          "number_of_pixels and the grid centre must have two values.");
  fPixelSize = {pixel_size[0], pixel_size[1]};
  fNumberOfPixels = {number_of_pixels[0], number_of_pixels[1]};
  fGridCenter = {center[0], center[1]};
}

void GateDigitizerChargeInductionActor::SetPixelVolume(
    const int depth, const std::vector<int> &copy_to_ix,
    const std::vector<int> &copy_to_iy) {
  if (copy_to_ix.size() != copy_to_iy.size())
    Fatal("Error in GateDigitizerChargeInductionActor: SetPixelVolume, the "
          "two lists must have the same size.");
  fPixelDepth = depth;
  fCopyToIx = copy_to_ix;
  fCopyToIy = copy_to_iy;
}

void GateDigitizerChargeInductionActor::SetCrystalDepth(const int depth) {
  fCrystalDepth = depth;
}

void GateDigitizerChargeInductionActor::SetCrystalThickness(const double t) {
  fThickness = t;
}

void GateDigitizerChargeInductionActor::SetTables(
    const py::array_t<double, py::array::c_style | py::array::forcecast> &own,
    const py::array_t<double, py::array::c_style | py::array::forcecast>
        &neighbour,
    const std::vector<double> &origin, const std::vector<double> &spacing) {
  if (own.ndim() != 3 || neighbour.ndim() != 3)
    Fatal("Error in GateDigitizerChargeInductionActor: the tables must be 3D");
  for (int i = 0; i < 3; i++) {
    if (own.shape(i) != neighbour.shape(i))
      Fatal("Error in GateDigitizerChargeInductionActor: the two tables must "
            "have the same shape");
    if (own.shape(i) < 2)
      Fatal("Error in GateDigitizerChargeInductionActor: the tables must have "
            "at least 2 nodes along each axis");
    fTableShape[i] = static_cast<int>(own.shape(i));
  }
  if (origin.size() != 3 || spacing.size() != 3)
    Fatal("Error in GateDigitizerChargeInductionActor: origin and spacing of "
          "the tables must have 3 values");
  for (int i = 0; i < 3; i++) {
    if (spacing[i] <= 0)
      Fatal("Error in GateDigitizerChargeInductionActor: the spacing of the "
            "tables must be positive");
    fTableOrigin[i] = origin[i];
    fTableSpacing[i] = spacing[i];
  }
  fCloudFlag = false; // set by SetCloudTables, if any
  fEtaOwn.assign(own.data(), own.data() + own.size());
  fEtaNeighbour.assign(neighbour.data(), neighbour.data() + neighbour.size());
}

double GateDigitizerChargeInductionActor::GetEta(const bool own, const double z,
                                                 const double dx,
                                                 const double dy) const {
  return Eta(own, z, dx, dy);
}

double GateDigitizerChargeInductionActor::Eta(const bool own, const double z,
                                              const double dx,
                                              const double dy) const {
  double eta = Interpolate(own ? fEtaOwn : fEtaNeighbour, z, dx, dy);
  if (fCloudFlag)
    eta += (fCloudX(dx) * fCloudY(dy) - (own ? 1.0 : 0.0)) * fCloudZ(z);
  return eta;
}

double
GateDigitizerChargeInductionActor::Table1D::operator()(const double p) const {
  // linear interpolation, clamped at the borders
  const int n = static_cast<int>(fValues.size());
  double c = (p - fOrigin) / fSpacing;
  if (c <= 0)
    return fValues[0];
  if (c >= n - 1)
    return fValues[n - 1];
  const int i = static_cast<int>(c);
  const double f = c - i;
  return (1 - f) * fValues[i] + f * fValues[i + 1];
}

void GateDigitizerChargeInductionActor::SetCloudTables(
    const std::vector<double> &fx, const double x0, const double dx,
    const std::vector<double> &fy, const double y0, const double dy,
    const std::vector<double> &fz, const double z0, const double dz) {
  if (fx.size() < 2 || fy.size() < 2 || fz.size() < 2 || dx <= 0 || dy <= 0 ||
      dz <= 0)
    Fatal("Error in GateDigitizerChargeInductionActor: the cloud tables must "
          "have at least 2 nodes and a positive spacing");
  fCloudX = {fx, x0, dx};
  fCloudY = {fy, y0, dy};
  fCloudZ = {fz, z0, dz};
  fCloudFlag = true;
}

double
GateDigitizerChargeInductionActor::Interpolate(const std::vector<double> &table,
                                               const double z, const double x,
                                               const double y) const {
  // trilinear interpolation, coordinates clamped to the grid (as
  // scipy.ndimage.map_coordinates with order=1 and mode="nearest")
  const double p[3] = {z, x, y};
  int i0[3];
  double f[3];
  for (int k = 0; k < 3; k++) {
    const int n = fTableShape[k];
    double c = (p[k] - fTableOrigin[k]) / fTableSpacing[k];
    if (c < 0)
      c = 0;
    if (c > n - 1)
      c = n - 1;
    int i = static_cast<int>(std::floor(c));
    if (i > n - 2)
      i = n - 2;
    i0[k] = i;
    f[k] = c - i;
  }
  const int nx = fTableShape[1];
  const int ny = fTableShape[2];
  auto at = [&](const int iz, const int ix, const int iy) {
    return table[(static_cast<size_t>(iz) * nx + ix) * ny + iy];
  };
  double v = 0;
  for (int a = 0; a < 2; a++) {
    const double wz = a ? f[0] : 1 - f[0];
    for (int b = 0; b < 2; b++) {
      const double wx = b ? f[1] : 1 - f[1];
      for (int c = 0; c < 2; c++) {
        const double wy = c ? f[2] : 1 - f[2];
        v += wz * wx * wy * at(i0[0] + a, i0[1] + b, i0[2] + c);
      }
    }
  }
  return v;
}

void GateDigitizerChargeInductionActor::StartSimulationAction() {
  // Init output (do not initialize root because attributes are added)
  fInitializeRootTupleForMasterFlag = false;
  GateVDigitizerWithOutputActor::StartSimulationAction();
  fInitializeRootTupleForMasterFlag = true;
  fIgnoredHitsCount = 0;

  // check required attributes
  CheckRequiredAttribute(fInputDigiCollection, "TotalEnergyDeposit");
  CheckRequiredAttribute(fInputDigiCollection, "PostPosition");
  CheckRequiredAttribute(fInputDigiCollection, "PreStepUniqueVolumeID");
  CheckRequiredAttribute(fInputDigiCollection, "GlobalTime");
  if (fMiddlePositionFlag)
    CheckRequiredAttribute(fInputDigiCollection, "PrePosition");
  fAttributePolicies.Check(fInputDigiCollection,
                           {"TotalEnergyDeposit", "PostPosition",
                            "PostPositionLocal", "GlobalTime", "PixelIndexX",
                            "PixelIndexY"});

  // check parameters
  if (fCrystalDepth < 0)
    Fatal("Error in GateDigitizerChargeInductionActor: the depth of the "
          "crystal is not set");
  if (fThickness <= 0)
    Fatal("Error in GateDigitizerChargeInductionActor: the thickness of the "
          "crystal is not set");
  if (fEtaOwn.empty())
    Fatal("Error in GateDigitizerChargeInductionActor: the tables are not set");
  if (fPixelSize[0] <= 0 || fPixelSize[1] <= 0 || fNumberOfPixels[0] <= 0 ||
      fNumberOfPixels[1] <= 0)
    Fatal("Error in GateDigitizerChargeInductionActor: pixel_size and "
          "number_of_pixels must be positive");
  if (fNeighbours != 0 && fNeighbours != 1)
    Fatal("Error in GateDigitizerChargeInductionActor: neighbours must be 0 or "
          "1");

  // add the attributes computed here
  if (!fOutputDigiCollection->IsDigiAttributeExists("PostPositionLocal")) {
    fAddPostPositionLocal = true;
    fOutputDigiCollection->InitDigiAttribute(
        new GateTDigiAttribute<G4ThreeVector>("PostPositionLocal"));
  }
  for (const auto *name : {"PixelIndexX", "PixelIndexY"}) {
    if (fOutputDigiCollection->IsDigiAttributeExists(name))
      Fatal(std::string("Error in GateDigitizerChargeInductionActor: the input "
                        "collection already contains the attribute ") +
            name);
    fOutputDigiCollection->InitDigiAttribute(new GateTDigiAttribute<int>(name));
  }
  fOutputDigiCollection->RootInitializeTupleForMaster();
  AddOutputTreeInfo(fOutputNameRoot, fOutputDigiCollection);
}

void GateDigitizerChargeInductionActor::DigitInitialize(
    const std::vector<std::string> &attributes_not_in_filler) {
  // remove the attributes computed here
  std::vector<std::string> att = attributes_not_in_filler;
  att.emplace_back("TotalEnergyDeposit");
  att.emplace_back("PostPosition");
  att.emplace_back("PostPositionLocal");
  att.emplace_back("GlobalTime");
  att.emplace_back("PixelIndexX");
  att.emplace_back("PixelIndexY");
  fAttributePolicies.AppendNames(att);
  GateVDigitizerWithOutputActor::DigitInitialize(att);
  fAttributePolicies.SetCollections(fInputDigiCollection,
                                    fOutputDigiCollection);

  fOutputEdepAttribute =
      fOutputDigiCollection->GetDigiAttribute("TotalEnergyDeposit");
  fOutputPosAttribute = fOutputDigiCollection->GetDigiAttribute("PostPosition");
  fOutputLocalPosAttribute =
      fOutputDigiCollection->GetDigiAttribute("PostPositionLocal");
  fOutputGlobalTimeAttribute =
      fOutputDigiCollection->GetDigiAttribute("GlobalTime");
  fOutputPixelIndexXAttribute =
      fOutputDigiCollection->GetDigiAttribute("PixelIndexX");
  fOutputPixelIndexYAttribute =
      fOutputDigiCollection->GetDigiAttribute("PixelIndexY");

  auto &l = fThreadLocalData.Get();
  auto &lr = fThreadLocalVDigitizerData.Get();
  lr.fInputIter = fInputDigiCollection->NewIterator();
  lr.fInputIter.TrackAttribute("TotalEnergyDeposit", &l.edep);
  lr.fInputIter.TrackAttribute("PostPosition", &l.pos);
  lr.fInputIter.TrackAttribute("PreStepUniqueVolumeID", &l.volID);
  lr.fInputIter.TrackAttribute("GlobalTime", &l.time);
  if (fMiddlePositionFlag)
    lr.fInputIter.TrackAttribute("PrePosition", &l.prePos);
  if (fInputDigiCollection->IsDigiAttributeExists("Weight")) {
    lr.fInputIter.TrackAttribute("Weight", &l.weight);
    fWeightsAreUsedFlag = true;
  }
  l.fIgnoredHitsCount = 0;
}

void GateDigitizerChargeInductionActor::ProcessHit() {
  auto &l = fThreadLocalData.Get();
  const auto &lr = fThreadLocalVDigitizerData.Get();
  const auto index = lr.fInputIter.fIndex;
  const double edep = *l.edep;
  if (edep == 0)
    return;

  // local position in the crystal
  const auto &volID = *l.volID;
  const auto &history = volID->fTouchable;
  if (static_cast<int>(history.GetDepth()) < fCrystalDepth) {
    l.fIgnoredHitsCount++;
    return;
  }
  const auto &toLocal = history.GetTransform(fCrystalDepth);
  G4ThreeVector p = *l.pos;
  if (fMiddlePositionFlag)
    p = 0.5 * (p + *l.prePos);
  const auto loc = toLocal.TransformPoint(p);

  // pixel of the hit: from the copy number of the pixel volume if any (hits
  // that are not in a pixel volume are ignored), otherwise from the local
  // position
  int ix[2] = {-1, -1};
  const double lxy[2] = {loc.x(), loc.y()};
  if (fPixelDepth >= 0) {
    int copy = -1;
    if (static_cast<int>(history.GetDepth()) >= fPixelDepth)
      copy = history.GetReplicaNo(fPixelDepth);
    if (copy < 0 || copy >= static_cast<int>(fCopyToIx.size())) {
      l.fIgnoredHitsCount++;
      return;
    }
    ix[0] = fCopyToIx[copy];
    ix[1] = fCopyToIy[copy];
  }
  if (ix[0] < 0) {
    for (int k = 0; k < 2; k++) {
      const double u =
          (lxy[k] - fGridCenter[k] + fNumberOfPixels[k] * fPixelSize[k] / 2.0) /
          fPixelSize[k];
      int i = static_cast<int>(std::floor(u));
      if (i < 0)
        i = 0;
      if (i > fNumberOfPixels[k] - 1)
        i = fNumberOfPixels[k] - 1;
      ix[k] = i;
    }
  }
  // position of the hit relative to the centre of its pixel
  double r[2];
  for (int k = 0; k < 2; k++)
    r[k] = lxy[k] - PixelCenter(k, ix[k]);

  // depth: distance to the cathode
  double z =
      fCathodeIsPlusZ ? fThickness / 2.0 - loc.z() : fThickness / 2.0 + loc.z();
  if (z < 0)
    z = 0;
  if (z > fThickness)
    z = fThickness;

  // key: volume (up to the crystal depth) and weight
  PixelKey key{};
  key.volumeID =
      static_cast<uint64_t>(volID->GetIdUpToDepthAsHash(fCrystalDepth));
  key.weightBits = 0;
  if (fWeightsAreUsedFlag)
    std::memcpy(&key.weightBits, l.weight, sizeof(double));

  const double t = *l.time;
  for (int a = -fNeighbours; a <= fNeighbours; a++) {
    const int jx = ix[0] + a;
    if (jx < 0 || jx >= fNumberOfPixels[0])
      continue;
    for (int b = -fNeighbours; b <= fNeighbours; b++) {
      const int jy = ix[1] + b;
      if (jy < 0 || jy >= fNumberOfPixels[1])
        continue;
      const bool own = a == 0 && b == 0;
      const double dx = r[0] - a * fPixelSize[0];
      const double dy = r[1] - b * fPixelSize[1];
      const double contrib = edep * Eta(own, z, dx, dy);
      key.pixel = jx * fNumberOfPixels[1] + jy;
      auto it = l.fPixels.find(key);
      if (it == l.fPixels.end()) {
        it = l.fPixels.emplace(key, PixelSignal{}).first;
        auto &ps = it->second;
        ps.fIx = jx;
        ps.fIy = jy;
        ps.fToGlobal = toLocal.Inverse();
      }
      auto &ps = it->second;
      ps.fSignal += contrib;
      if (t < ps.fTime)
        ps.fTime = t;
      if (std::abs(contrib) > ps.fBestScore) {
        ps.fBestScore = std::abs(contrib);
        ps.fBestIndex = index;
      }
      fAttributePolicies.Update(ps.fAttributeTracker, index, t,
                                std::abs(contrib));
    }
  }
}

void GateDigitizerChargeInductionActor::EndOfEventAction(
    const G4Event * /*event*/) {
  auto &l = fThreadLocalData.Get();
  auto &lr = fThreadLocalVDigitizerData.Get();
  auto &iter = lr.fInputIter;
  iter.GoToBegin();
  while (!iter.IsAtEnd()) {
    ProcessHit();
    iter++;
  }

  for (const auto &item : l.fPixels) {
    const auto &ps = item.second;
    const double s = ps.fSignal * fGain;
    if (s < fThreshold || s <= 0)
      continue;
    const G4ThreeVector local(PixelCenter(0, ps.fIx), PixelCenter(1, ps.fIy),
                              0);
    const auto global = ps.fToGlobal.TransformPoint(local);
    fOutputEdepAttribute->FillDValue(s);
    fOutputPosAttribute->Fill3Value(global);
    fOutputLocalPosAttribute->Fill3Value(local);
    fOutputGlobalTimeAttribute->FillDValue(ps.fTime);
    fOutputPixelIndexXAttribute->FillIValue(ps.fIx);
    fOutputPixelIndexYAttribute->FillIValue(ps.fIy);
    fAttributePolicies.Fill(ps.fAttributeTracker);
    lr.fDigiAttributeFiller->Fill(ps.fBestIndex);
  }
  l.fPixels.clear();
}

void GateDigitizerChargeInductionActor::EndOfSimulationWorkerAction(
    const G4Run *lastRun) {
  {
    G4AutoLock mutex(&ChargeInductionIgnoredHitsMutex);
    fIgnoredHitsCount += fThreadLocalData.Get().fIgnoredHitsCount;
  }
  GateVDigitizerWithOutputActor::EndOfSimulationWorkerAction(lastRun);
}
