/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#include "GateCoincidenceSorterActor.h"
#include "../GateHelpersDict.h"
#include "GateDigiCollectionManager.h"
#include <algorithm>
#include <limits>
#include <memory>
#include <numeric>

GateCoincidenceSorterActor::TemporaryStorage::TemporaryStorage(
    GateDigiCollection *input, GateDigiCollection *output,
    const std::string &name_suffix) {

  auto *manager = GateDigiCollectionManager::GetInstance();
  const auto attribute_names = input->GetDigiAttributeNames();

  // GateDigiCollection for temporary storage
  // TODO name OK?
  digis = manager->NewDigiCollection(input->GetName() + "_" + name_suffix);
  digis->InitDigiAttributesFromCopy(input);

  iter = digis->NewIterator();
  iter.TrackAttribute("GlobalTime", &currentTime);
  iter.TrackAttribute("PreStepUniqueVolumeID", &currentVolID);
  iter.TrackAttribute("PostPosition", &currentPos);
  iter.TrackAttribute("TotalEnergyDeposit", &currentEdep);

  // Filler to copy from input collection to temporary collection
  fillerIn =
      std::make_unique<GateDigiAttributesFiller>(input, digis, attribute_names);

  // Filler to copy from temporary to output collection
  fillerOut = std::make_unique<GateCoincidenceDigiAttributesFiller>(
      digis, output, attribute_names);
}

GateCoincidenceSorterActor::GateCoincidenceSorterActor(py::dict &user_info)
    : GateVDigitizerWithOutputActor(user_info, false) {
  fActions.insert("StartSimulationAction");
  fActions.insert("EndOfEventAction");
  fActions.insert("EndOfRunAction");
}

GateCoincidenceSorterActor::~GateCoincidenceSorterActor() = default;

void GateCoincidenceSorterActor::InitializeUserInfo(py::dict &user_info) {

  GateVDigitizerWithOutputActor::InitializeUserInfo(user_info);
  if (py::len(user_info) > 0 && user_info.contains("window")) {
    fWindowSize = DictGetDouble(user_info, "window"); // nanoseconds
  }
  if (py::len(user_info) > 0 && user_info.contains("offset")) {
    fWindowOffset = DictGetDouble(user_info, "offset"); // nanoseconds
  }
  if (py::len(user_info) > 0 && user_info.contains("multiples_policy")) {
    const auto policy_str = DictGetStr(user_info, "multiples_policy");
    if (policy_str == "RemoveMultiples") {
      fMultiplesPolicy = MultiplesPolicy::RemoveMultiples;
    } else if (policy_str == "TakeAllGoods") {
      fMultiplesPolicy = MultiplesPolicy::TakeAllGoods;
    } else if (policy_str == "TakeWinnerOfGoods") {
      fMultiplesPolicy = MultiplesPolicy::TakeWinnerOfGoods;
    } else if (policy_str == "TakeIfOnlyOneGood") {
      fMultiplesPolicy = MultiplesPolicy::TakeIfOnlyOneGood;
    } else if (policy_str == "TakeWinnerIfIsGood") {
      fMultiplesPolicy = MultiplesPolicy::TakeWinnerIfIsGood;
    } else if (policy_str == "TakeWinnerIfAllAreGoods") {
      fMultiplesPolicy = MultiplesPolicy::TakeWinnerIfAllAreGoods;
    } else {
      Fatal("Unknown multiples policy '" + policy_str + "'");
    }
  }
  if (py::len(user_info) > 0 && user_info.contains("multi_window")) {
    fMultiWindow = DictGetDouble(user_info, "multi_window");
  }
  if (py::len(user_info) > 0 && user_info.contains("min_transaxial_distance")) {
    const auto value = user_info.attr("min_transaxial_distance");
    if (!value.is_none()) {
      const auto d = DictGetDouble(user_info, "min_transaxial_distance");
      fMinTransaxialDistance2 = d * d;
    }
  }
  if (py::len(user_info) > 0 && user_info.contains("max_axial_distance")) {
    const auto value = user_info.attr("max_axial_distance");
    if (!value.is_none()) {
      fMaxAxialDistance = DictGetDouble(user_info, "max_axial_distance");
    }
  }
  if (py::len(user_info) > 0 && user_info.contains("transaxial_plane")) {
    const auto transaxial_plane_str = DictGetStr(user_info, "transaxial_plane");
    if (transaxial_plane_str == "XY") {
      fTransaxialPlane = TransaxialPlane::XY;
    } else if (transaxial_plane_str == "YZ") {
      fTransaxialPlane = TransaxialPlane::YZ;
    } else if (transaxial_plane_str == "XZ") {
      fTransaxialPlane = TransaxialPlane::XZ;
    } else {
      Fatal("Unknown transaxial plane '" + transaxial_plane_str + "'");
    }
  }
  if (py::len(user_info) > 0 && user_info.contains("sorting_time")) {
    fSortingTime = DictGetDouble(user_info, "sorting_time"); // nanoseconds
  }
  fGroupVolumeDepth = -1;
  fInputDigiCollectionName = DictGetStr(user_info, "input_digi_collection");
}

void GateCoincidenceSorterActor::StartSimulationAction() {

  // Get the input hits collection
  auto *hcm = GateDigiCollectionManager::GetInstance();
  fInputDigiCollection = hcm->GetDigiCollection(fInputDigiCollectionName);

  // Create the list of output attributes
  fOutputDigiCollection = hcm->NewDigiCollection(fOutputDigiCollectionName);
  std::string outputPath;
  if (!GetWriteToDisk(fOutputNameRoot)) {
    outputPath = "";
  } else {
    outputPath = GetOutputPath(fOutputNameRoot);
  }
  fOutputDigiCollection->SetFilenameAndInitRoot(outputPath);

  const auto attribute_names = fInputDigiCollection->GetDigiAttributeNames();
  const std::string suffix1 = "1";
  const std::string suffix2 = "2";
  for (const auto &name : attribute_names) {
    if (std::find(fUserSkipDigiAttributeNames.begin(),
                  fUserSkipDigiAttributeNames.end(),
                  name) != fUserSkipDigiAttributeNames.end()) {
      continue;
    }
    const auto att_type =
        fInputDigiCollection->GetDigiAttribute(name)->GetDigiAttributeType();
    GateVDigiAttribute *att1{};
    GateVDigiAttribute *att2{};
    if (att_type == 'D') {
      att1 = new GateTDigiAttribute<double>(name + suffix1);
      att2 = new GateTDigiAttribute<double>(name + suffix2);
    } else if (att_type == 'I') {
      att1 = new GateTDigiAttribute<int>(name + suffix1);
      att2 = new GateTDigiAttribute<int>(name + suffix2);
    } else if (att_type == 'L') {
      att1 = new GateTDigiAttribute<int64_t>(name + suffix1);
      att2 = new GateTDigiAttribute<int64_t>(name + suffix2);
    } else if (att_type == 'S') {
      att1 = new GateTDigiAttribute<std::string>(name + suffix1);
      att2 = new GateTDigiAttribute<std::string>(name + suffix2);
    } else if (att_type == '3') {
      att1 = new GateTDigiAttribute<G4ThreeVector>(name + suffix1);
      att2 = new GateTDigiAttribute<G4ThreeVector>(name + suffix2);
    } else if (att_type == 'U') {
      att1 =
          new GateTDigiAttribute<GateUniqueVolumeID::Pointer>(name + suffix1);
      att2 =
          new GateTDigiAttribute<GateUniqueVolumeID::Pointer>(name + suffix2);
    } else {
      Fatal("Unknown digi attribute type '" + std::string(1, att_type) + "'");
    }
    fOutputDigiCollection->InitDigiAttribute(att1);
    fOutputDigiCollection->InitDigiAttribute(att2);
  }

  if (fInitializeRootTupleForMasterFlag) {
    fOutputDigiCollection->RootInitializeTupleForMaster();
  }
}

void GateCoincidenceSorterActor::SetGroupVolumeDepth(const int depth) {
  fGroupVolumeDepth = depth;
}

void GateCoincidenceSorterActor::DigitInitialize(
    const std::vector<std::string> &attributes_not_in_filler) {

  // Set up pointers to track specific attributes
  auto &lr = fThreadLocalVDigitizerData.Get();
  auto &l = fThreadLocalData.Get();

  fTimeSorter.Init(fInputDigiCollection);
  fTimeSorter.OutputIterator().TrackAttribute("GlobalTime", &l.time);
  fTimeSorter.OutputIterator().TrackAttribute("PreStepUniqueVolumeID",
                                              &l.volID);
  fTimeSorter.SetSortingWindow(fSortingTime);
  fTimeSorter.SetMaxSize(fClearEveryNEvents);

  fCurrentStorage = std::make_unique<TemporaryStorage>(
      fTimeSorter.OutputCollection(), fOutputDigiCollection, "A");
  fFutureStorage = std::make_unique<TemporaryStorage>(
      fTimeSorter.OutputCollection(), fOutputDigiCollection, "B");
}

void GateCoincidenceSorterActor::EndOfEventAction(const G4Event *) {
  auto &l = fThreadLocalData.Get();
  fTimeSorter.Process();
  ProcessTimeSortedSingles();
  DetectCoincidences();
}

void GateCoincidenceSorterActor::EndOfRunAction(const G4Run *) {
  fTimeSorter.Flush();
  ProcessTimeSortedSingles();
  DetectCoincidences(true);
  fOutputDigiCollection->FillToRootIfNeeded(true);
}

void GateCoincidenceSorterActor::ProcessTimeSortedSingles() {
  auto &l = fThreadLocalData.Get();
  auto &iter = fTimeSorter.OutputIterator();
  iter.GoToBegin();
  while (!iter.IsAtEnd()) {
    fCurrentStorage->fillerIn->Fill(iter.fIndex);
    if (!fCurrentStorage->earliestTime) {
      fCurrentStorage->earliestTime = *l.time;
    }
    fCurrentStorage->latestTime = *l.time;
    iter++;
  }
  fTimeSorter.MarkOutputAsProcessed();
}

void GateCoincidenceSorterActor::DetectCoincidences(bool lastCall) {

  if (fCurrentStorage->earliestTime && fCurrentStorage->latestTime) {
    auto &iter = fCurrentStorage->iter;
    auto &t = fCurrentStorage->currentTime;
    auto &v = fCurrentStorage->currentVolID;
    auto &p = fCurrentStorage->currentPos;
    auto &e = fCurrentStorage->currentEdep;

    iter.GoToBegin();
    while ((*fCurrentStorage->latestTime - *fCurrentStorage->earliestTime >
            fWindowSize + fWindowOffset) ||
           (lastCall &&
            *fCurrentStorage->latestTime - *fCurrentStorage->earliestTime >
                fWindowOffset)) {

      const auto i0 = iter.fIndex;
      const auto t0 = *t;
      const auto v0 = v->get()->GetIdUpToDepthAsHash(fGroupVolumeDepth);
      const auto p0 = *p;
      std::vector<size_t> secondSingleIndex;
      std::vector<double> secondSingleEdep;
      std::vector<uint8_t> goodCoincidence;
      iter++;
      while (!iter.IsAtEnd()) {
        const auto deltaT = *t - t0;
        if (fWindowOffset <= deltaT && deltaT <= fWindowOffset + fWindowSize) {
          if (v->get()->GetIdUpToDepthAsHash(fGroupVolumeDepth) != v0) {
            secondSingleIndex.push_back(iter.fIndex);
            secondSingleEdep.push_back(*e);
            goodCoincidence.push_back(CoincidenceIsGood(p0, *p) ? 1 : 0);
          }
        }
        if (deltaT > fWindowOffset + fWindowSize) {
          break;
        }
        iter++;
      }
      const auto numCoincidences = secondSingleIndex.size();
      if (numCoincidences == 1) {
        fCurrentStorage->fillerOut->Fill(i0, secondSingleIndex[0]);
      } else if (numCoincidences > 1) {
        const auto filteredIndices =
            ApplyPolicy(secondSingleIndex, secondSingleEdep, goodCoincidence);
        for (auto index : filteredIndices) {
          fCurrentStorage->fillerOut->Fill(i0, index);
        }
      }
      iter.GoToBegin();

      if (fMultiWindow) {
        fCurrentStorage->digis->SetBeginOfEventIndex(iter.fIndex + 1);
      } else {
        fCurrentStorage->digis->SetBeginOfEventIndex(iter.fIndex + 1 +
                                                     numCoincidences);
      }
      iter.GoToBegin();
      if (iter.IsAtEnd()) {
        break;
      }
      fCurrentStorage->earliestTime = *t;

      // TODO: swap fCurrentStorage and fFutureStorage when fCurrentStorage has
      // grown too large.
    }
  }
}

bool GateCoincidenceSorterActor::CoincidenceIsGood(
    const G4ThreeVector &pos1, const G4ThreeVector &pos2) const {
  if (!fMaxAxialDistance && !fMinTransaxialDistance2) {
    return true;
  }
  bool good = true;
  const auto dx = pos1.x() - pos2.x();
  const auto dy = pos1.y() - pos2.y();
  const auto dz = pos1.z() - pos2.z();
  if (fMaxAxialDistance) {
    if (TransaxialPlane::XY == fTransaxialPlane) {
      good = std::abs(dz) <= *fMaxAxialDistance;
    } else if (TransaxialPlane::XZ == fTransaxialPlane) {
      good = std::abs(dy) <= *fMaxAxialDistance;
    } else if (TransaxialPlane::YZ == fTransaxialPlane) {
      good = std::abs(dx) <= *fMaxAxialDistance;
    }
  }
  if (good && fMinTransaxialDistance2) {
    if (TransaxialPlane::XY == fTransaxialPlane) {
      good = dx * dx + dy * dy >= *fMinTransaxialDistance2;
    } else if (TransaxialPlane::XZ == fTransaxialPlane) {
      good = dy * dy + dy * dy >= *fMinTransaxialDistance2;
    } else if (TransaxialPlane::YZ == fTransaxialPlane) {
      good = dy * dy + dz * dz >= *fMinTransaxialDistance2;
    }
  }
  return good;
}

std::vector<size_t> GateCoincidenceSorterActor::ApplyPolicy(
    const std::vector<size_t> &secondSingleIndex,
    const std::vector<double> &secondSingleEdep,
    const std::vector<uint8_t> &goodCoincidence) const {

  const auto numCoincidences = secondSingleIndex.size();
  std::vector<size_t> filteredIndices;
  const auto &gc = goodCoincidence;
  const auto &sse = secondSingleEdep;
  const auto &ssi = secondSingleIndex;

  if (MultiplesPolicy::TakeAllGoods == fMultiplesPolicy) {
    for (size_t i = 0; i < numCoincidences; ++i) {
      if (gc[i]) {
        filteredIndices.push_back(ssi[i]);
      }
    }
  } else if (MultiplesPolicy::TakeIfOnlyOneGood == fMultiplesPolicy) {
    const auto numGoods = std::accumulate(gc.begin(), gc.end(), size_t(0));
    if (numGoods == 1) {
      const auto it = std::find(gc.begin(), gc.end(), 1);
      const auto index = std::distance(gc.begin(), it);
      filteredIndices.push_back(ssi[index]);
    }
  } else if (MultiplesPolicy::TakeWinnerOfGoods == fMultiplesPolicy) {
    const auto numGoods = std::accumulate(gc.begin(), gc.end(), 0);
    if (numGoods >= 1) {
      double maxEdep = std::numeric_limits<double>::min();
      size_t index = 0;
      for (size_t i = 0; i < numCoincidences; ++i) {
        if (gc[i] && sse[i] > maxEdep) {
          maxEdep = sse[i];
          index = i;
        }
      }
      filteredIndices.push_back(ssi[index]);
    }
  } else if (MultiplesPolicy::TakeWinnerIfIsGood == fMultiplesPolicy) {
    const auto maxIt = std::max_element(sse.begin(), sse.end());
    const size_t winnerIndex = std::distance(sse.begin(), maxIt);
    if (gc[winnerIndex]) {
      filteredIndices.push_back(ssi[winnerIndex]);
    }
  } else if (MultiplesPolicy::TakeWinnerIfAllAreGoods == fMultiplesPolicy) {
    const auto numGoods = std::accumulate(gc.begin(), gc.end(), 0);
    if (numGoods == numCoincidences) {
      const auto maxIt = std::max_element(sse.begin(), sse.end());
      const size_t winnerIndex = std::distance(sse.begin(), maxIt);
      filteredIndices.push_back(ssi[winnerIndex]);
    }
  }
  // MultiplesPolicy::RemoveMultiples: do nothing.

  return filteredIndices;
}
