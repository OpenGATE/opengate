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
  digis = manager->NewDigiCollection(input->GetName() + "_" + name_suffix);
  digis->InitDigiAttributesFromCopy(input);
  digis->SetSharedStorage(true);

  // Filler to copy from input collection to temporary collection
  fillerIn =
      std::make_unique<GateDigiAttributesFiller>(input, digis, attribute_names);

  // Filler to copy from temporary to output collection
  fillerOut = std::make_unique<GateCoincidenceDigiAttributesFiller>(
      digis, output, attribute_names);
}

GateCoincidenceSorterActor::GateCoincidenceSorterActor(py::dict &user_info)
    : GateVDigitizerWithOutputActor(user_info, true) {
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

  // Create the attributes for coincidence digis. They have the same names as
  // the attributes of the single digis, but with a "1" or "2" suffix (for the
  // first and second single in the coincidence pair).
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

void GateCoincidenceSorterActor::BeginOfRunActionMasterThread(int run_id) {

  // Create, initialize and configure the time sorter.
  // The time sorter will create a single time-sorted stream containing all
  // digis from all threads, so that the coincidence actor can identify
  // coincidences between singles, irrespective of the thread in which they were
  // simulated (prompt as well as random coincidences).
  fTimeSorter = std::make_unique<GateTimeSorter>();
  fTimeSorter->Init(fInputDigiCollection);
  fTimeSorter->SetSortingWindow(fSortingTime);
  fTimeSorter->SetMaxSize(fClearEveryNEvents);

  // Create temporary storage, which stores time-sorted digis until a
  // sufficiently large GlobalTime range is covered to allow for coincidence
  // detection.
  // The memory consumption of the "current" temporary storage grows as the
  // simulation progresses, because already processed digis remain in the
  // storage. For that reason, a second "future" temporary storage is created,
  // which will be used later for taking over the not-yet-processed digis, so
  // that the "current" one can be cleared to reclaim memory.
  fCurrentStorage = std::make_unique<TemporaryStorage>(
      fTimeSorter->OutputCollection(), fOutputDigiCollection, "A");
  fFutureStorage = std::make_unique<TemporaryStorage>(
      fTimeSorter->OutputCollection(), fOutputDigiCollection, "B");
}

void GateCoincidenceSorterActor::SetGroupVolumeDepth(const int depth) {
  fGroupVolumeDepth = depth;
}

void GateCoincidenceSorterActor::DigitInitialize(
    const std::vector<std::string> &attributes_not_in_filler) {
  fOutputDigiCollection->RootInitializeTupleForWorker();
}

void GateCoincidenceSorterActor::EndOfEventAction(const G4Event *) {

  fTimeSorter->OnEndOfEventAction([this]() {
    ProcessTimeSortedSingles();
    DetectCoincidences();
  });
}

void GateCoincidenceSorterActor::EndOfRunAction(const G4Run *) {

  fTimeSorter->OnEndOfRunAction(
      [this]() { fOutputDigiCollection->FillToRootIfNeeded(true); },
      [this]() {
        ProcessTimeSortedSingles();
        DetectCoincidences(true);
        ClearProcessedSingles();
      });
}

void GateCoincidenceSorterActor::ProcessTimeSortedSingles() {

  // Copies digis from the output of the time sorter to the temporary storage,
  // while keeping track GlobalTime of the most recently copied digi.

  auto &timeVec = fTimeSorter->OutputCollection()
                      ->GetDigiAttribute("GlobalTime")
                      ->GetDValues();
  auto &iter = fTimeSorter->OutputIterator();
  iter.GoToBegin();
  while (!iter.IsAtEnd()) {
    fCurrentStorage->fillerIn->Fill(iter.fIndex);
    const double t = timeVec[iter.fIndex];
    if (!fCurrentStorage->earliestTime) {
      fCurrentStorage->earliestTime = t;
    }
    fCurrentStorage->latestTime = t;
    iter++;
  }
  fTimeSorter->MarkOutputAsProcessed();
}

void GateCoincidenceSorterActor::DetectCoincidences(bool lastCall) {

  if (fCurrentStorage->earliestTime && fCurrentStorage->latestTime) {
    double *t;
    GateUniqueVolumeID::Pointer *v;
    G4ThreeVector *p;
    double *e;
    auto iter = fCurrentStorage->digis->NewIterator();
    iter.TrackAttribute("GlobalTime", &t);
    iter.TrackAttribute("PreStepUniqueVolumeID", &v);
    iter.TrackAttribute("PostPosition", &p);
    iter.TrackAttribute("TotalEnergyDeposit", &e);

    // Iterate over the time-sorted digis in the temporary storage, as long as
    // the GlobalTime difference between the oldest and newest digi in the
    // collection is at least equal to the coincidence window size + the window
    // offset.
    iter.fIndex = fIterPosition;
    iter.GoTo(fIterPosition);
    while ((*fCurrentStorage->latestTime - *fCurrentStorage->earliestTime >
            fWindowSize + fWindowOffset) ||
           (lastCall &&
            *fCurrentStorage->latestTime - *fCurrentStorage->earliestTime >
                fWindowOffset)) {

      // "0" refers to the oldest digi in the storage, which is the digi that
      // "opens the coincidence time window".
      const auto i0 = iter.fIndex;
      const auto t0 = *t;
      const auto v0 = v->get()->GetIdUpToDepthAsHash(fGroupVolumeDepth);
      const auto p0 = *p;
      // The digis that are in coincidence with digi "0" are referred to as the
      // "second" digis. The following vectors store their index in the
      // collection, their deposited energy, and whether they are a "good"
      // coincidence with digi "0". A "good" coincidence is one where the
      // location of both singles satisfy the minimal transaxial distance and
      // the maximal axial distance.
      std::vector<size_t> secondSingleIndex;
      std::vector<double> secondSingleEdep;
      std::vector<uint8_t> goodCoincidence;
      iter++;
      // Iterate over the "second" digis, as long as they are in the coincidence
      // window.
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
      // If there is only one coincidence in the window opened by digi "0", then
      // simply add the coincidence to the output collection.
      // If there are multiple, then first apply the multiples policy before
      // adding the remaining coincidences to the output collection.
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

      // If every digi can open a coincidence window, then advance the window to
      // the next digi, otherwise advance to the first digi beyond the current
      // coincidence window.
      if (fMultiWindow) {
        fIterPosition += 1;
      } else {
        fIterPosition += 1 + numCoincidences;
      }
      iter.fIndex = fIterPosition;
      iter.GoTo(fIterPosition);
      if (iter.IsAtEnd()) {
        break;
      }
      // The digi pointed to by the iterator is now the oldest one in the
      // temporary storage.
      fCurrentStorage->earliestTime = *t;
    }

    // If the temporary storage has grown too large, then reclaim the memory of
    // the digis that have already been processed.
    if (fCurrentStorage->digis->GetSize() >= fClearEveryNEvents) {
      ClearProcessedSingles();
    }
  }
}

bool GateCoincidenceSorterActor::CoincidenceIsGood(
    const G4ThreeVector &pos1, const G4ThreeVector &pos2) const {

  // Determines whether the given pair of digi locations satisfies the maximal
  // axial distance and the minimal transaxial distance.

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
      good = dx * dx + dz * dz >= *fMinTransaxialDistance2;
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

  // Applies the multiples policy, given the index, energy and "good"-ness of
  // the N "second" digis in the multiple coincidences.
  // The result is a vector containing between 0 and N indices, indicating which
  // coincidences satisfy the policy.

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
  // MultiplesPolicy::RemoveMultiples: do nothing, filteredIndices remains
  // empty.

  return filteredIndices;
}

void GateCoincidenceSorterActor::ClearProcessedSingles() {

  // Frees the memory occupied by already-processed digis:
  // copy the not-yet-processed digis and the earliest/latest time from the
  // "current" storage to the "future" storage, then clear the "current" storage
  // and swap the pointers of both storages.

  GateDigiAttributesFiller transferFiller(
      fCurrentStorage->digis, fFutureStorage->digis,
      fCurrentStorage->digis->GetDigiAttributeNames());

  auto iter = fCurrentStorage->digis->NewIterator();
  iter.fIndex = fIterPosition;
  iter.GoTo(fIterPosition);

  while (!iter.IsAtEnd()) {
    transferFiller.Fill(iter.fIndex);
    iter++;
  }

  fFutureStorage->earliestTime = fCurrentStorage->earliestTime;
  fFutureStorage->latestTime = fCurrentStorage->latestTime;

  fCurrentStorage->digis->Clear();
  fCurrentStorage->earliestTime.reset();
  fCurrentStorage->latestTime.reset();

  std::swap(fCurrentStorage, fFutureStorage);
  fIterPosition = 0;
}
