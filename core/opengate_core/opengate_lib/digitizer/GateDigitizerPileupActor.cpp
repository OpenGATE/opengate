/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#include "GateDigitizerPileupActor.h"
#include "../GateHelpers.h"
#include "../GateHelpersDict.h"
#include "GateDigiCollectionManager.h"
#include "GateHelpersDigitizer.h"
#include <memory>

GateDigitizerPileupActor::GateDigitizerPileupActor(py::dict &user_info)
    : GateVDigitizerWithOutputActor(user_info, true) {
  fActions.insert("EndOfEventAction");
  fActions.insert("EndOfRunAction");
}

GateDigitizerPileupActor::~GateDigitizerPileupActor() = default;

void GateDigitizerPileupActor::InitializeUserInfo(py::dict &user_info) {

  GateVDigitizerWithOutputActor::InitializeUserInfo(user_info);
  if (py::len(user_info) > 0 && user_info.contains("time_window")) {
    fTimeWindow = DictGetDouble(user_info, "time_window"); // nanoseconds
  }
  if (py::len(user_info) > 0 && user_info.contains("time_window_policy")) {
    const auto policy_str = DictGetStr(user_info, "time_window_policy");
    if (policy_str == "NonParalyzable") {
      fTimeWindowPolicy = TimeWindowPolicy::NonParalyzable;
    } else if (policy_str == "Paralyzable") {
      fTimeWindowPolicy = TimeWindowPolicy::Paralyzable;
    } else if (policy_str == "EnergyWinnerParalyzable") {
      fTimeWindowPolicy = TimeWindowPolicy::EnergyWinnerParalyzable;
    } else {
      Fatal("Unknown time window policy '" + policy_str + "'");
    }
  }
  if (py::len(user_info) > 0 &&
      user_info.contains("position_attribute_policy")) {
    const auto policy_str = DictGetStr(user_info, "position_attribute_policy");
    if (policy_str == "EnergyWinner") {
      fPositionAttributePolicy = PositionAttributePolicy::EnergyWinner;
    } else if (policy_str == "EnergyWeightedCentroid") {
      fPositionAttributePolicy =
          PositionAttributePolicy::EnergyWeightedCentroid;
    } else {
      Fatal("Unknown position attribute policy '" + policy_str + "'");
    }
  }
  if (py::len(user_info) > 0 && user_info.contains("attribute_policy")) {
    const auto policy_str = DictGetStr(user_info, "attribute_policy");
    if (policy_str == "First") {
      fAttributePolicy = AttributePolicy::First;
    } else if (policy_str == "EnergyWinner") {
      fAttributePolicy = AttributePolicy::EnergyWinner;
    } else if (policy_str == "Last") {
      fAttributePolicy = AttributePolicy::Last;
    } else {
      Fatal("Unknown attribute policy '" + policy_str + "'");
    }
  }

  if (py::len(user_info) > 0 && user_info.contains("sorting_time")) {
    fSortingTime = DictGetDouble(user_info, "sorting_time"); // nanoseconds
  }
  fGroupVolumeDepth = -1;
  fInputDigiCollectionName = DictGetStr(user_info, "input_digi_collection");
}

void GateDigitizerPileupActor::BeginOfRunActionMasterThread(int run_id) {

  fTimeSorter = std::make_unique<GateTimeSorter>(fOutputDigiCollectionName);
  fTimeSorter->Init(fInputDigiCollection);
  fTimeSorter->SetSortingWindow(fSortingTime);
  fTimeSorter->SetMaxSize(fClearEveryNEvents);

  auto &outputIter = fTimeSorter->OutputIterator();
  outputIter.TrackAttribute("GlobalTime", &fTimeSorterOutputTime);
  outputIter.TrackAttribute("TotalEnergyDeposit", &fTimeSorterOutputEdep);
  outputIter.TrackAttribute("PreStepUniqueVolumeID", &fTimeSorterOutputVolID);

  fVolumePileupWindows.clear();
  fWindowExpiry = std::queue<volumeWindowExpiry>();
}

void GateDigitizerPileupActor::SetGroupVolumeDepth(const int depth) {
  fGroupVolumeDepth = depth;
}

void GateDigitizerPileupActor::DigitInitialize(
    const std::vector<std::string> &attributes_not_in_filler) {

  auto a = attributes_not_in_filler;
  a.push_back("GlobalTime");
  a.push_back("TotalEnergyDeposit");
  a.push_back("PostPosition");
  GateVDigitizerWithOutputActor::DigitInitialize(a);

  fOutputDigiCollection->RootInitializeTupleForWorker();
}

void GateDigitizerPileupActor::EndOfEventAction(const G4Event *) {

  fTimeSorter->OnEndOfEventAction([this]() { ProcessTimeSortedDigis(); });
}

void GateDigitizerPileupActor::EndOfRunAction(const G4Run *) {

  fTimeSorter->OnEndOfRunAction(
      [this]() { fOutputDigiCollection->FillToRootIfNeeded(true); },
      [this]() {
        ProcessTimeSortedDigis();
        // Process all pile-up windows which still have an expiry item.
        while (fWindowExpiry.size() > 0) {
          auto &window =
              fVolumePileupWindows.at(fWindowExpiry.front().volumeHash);
          ProcessPileupWindow(window);
          fWindowExpiry.pop();
        }
      });
}

GateDigitizerPileupActor::PileupWindow &
GateDigitizerPileupActor::GetPileupWindowForCurrentVolume(
    GateUniqueVolumeID::Pointer *volume,
    std::map<uint64_t, PileupWindow> &windows) {
  // This function looks up the PileupWindow object for the given volume. If it
  // does not yet exist for the volume, it creates a PileupWindow.

  const auto vol_hash = volume->get()->GetIdUpToDepthAsHash(fGroupVolumeDepth);

  // Look up the window based on volume hash.
  auto it = windows.find(vol_hash);
  if (it != windows.end()) {
    // Return a reference to the existing PileupWindow object for the volume.
    return it->second;
  } else {
    // A PileupWindow object does not yet exist for this volume: create one.
    PileupWindow window;
    window.hash = vol_hash;
    const auto vol_id = volume->get()->GetIdUpToDepth(fGroupVolumeDepth);
    // Create a GateDigiCollection for this volume, as a temporary storage for
    // digis that belong to the same time window (the name must be unique).
    window.digis = GateDigiCollectionManager::GetInstance()->NewDigiCollection(
        GetName() + "_" + vol_id);
    window.digis->InitDigiAttributesFromCopy(fInputDigiCollection);
    window.digis->SetSharedStorage(
        true); // Same storage is accessible by all threads.
    // Create an iterator to be used when digis will be combined into one digi,
    // due to pile-up.
    window.digiIter = window.digis->NewIterator();
    window.digiIter.TrackAttribute("TotalEnergyDeposit", &fPileupWindowEdep);
    window.digiIter.TrackAttribute("PostPosition", &fPileupWindowPos);
    // Create a filler to copy all digi attributes from the sorted collection
    // into the collection of the window.
    window.fillerIn = std::make_unique<GateDigiAttributesFiller>(
        fTimeSorter->OutputCollection(), window.digis,
        fTimeSorter->OutputCollection()->GetDigiAttributeNames());
    // Create a filler to copy digi attributes from the collection of the window
    // to the output collection (used for the digis that will result from
    // pile-up).
    auto filler_out_attributes = window.digis->GetDigiAttributeNames();
    filler_out_attributes.erase("TotalEnergyDeposit");
    filler_out_attributes.erase("PostPosition");
    window.fillerOut = std::make_unique<GateDigiAttributesFiller>(
        window.digis, fOutputDigiCollection, filler_out_attributes);

    // Store the PileupWindow in the map and return a reference.
    windows[vol_hash] = std::move(window);
    return windows[vol_hash];
  }
}

void GateDigitizerPileupActor::ProcessTimeSortedDigis() {

  auto &iter = fTimeSorter->OutputIterator();
  iter.GoToBegin();
  while (!iter.IsAtEnd()) {
    // Look up or create the pile-up window object for the volume to which the
    // current digi belongs.
    auto &window = GetPileupWindowForCurrentVolume(fTimeSorterOutputVolID,
                                                   fVolumePileupWindows);

    const auto current_time = *fTimeSorterOutputTime;
    const auto current_edep = *fTimeSorterOutputEdep;

    // The GlobalTime of digis provided by the time sorter are guaranteed to be
    // monotonically increasing. As a consequence, all pile-up windows that have
    // expired by the time of the most recently arrived digi can be handled.
    ProcessPileupWindows(current_time);

    if (window.digis->GetSize() == 0) {
      // The window was empty: the newly arrived digi will open it.
      window.startTime = current_time;
      fWindowExpiry.push({window.hash, window.startTime + fTimeWindow});
      window.highestEdep = current_edep;
    } else {
      // The window was already opened: update the window depending on the
      // policy.
      switch (fTimeWindowPolicy) {
      case TimeWindowPolicy::NonParalyzable:
        // window start time remains the same.
        break;
      case TimeWindowPolicy::Paralyzable:
        // The current digi moves the start time forward.
        window.startTime = current_time;
        fWindowExpiry.push({window.hash, window.startTime + fTimeWindow});
        break;
      case TimeWindowPolicy::EnergyWinnerParalyzable:
        // The current digi moves the start time forward if its energy is higher
        // than previous energies.
        if (current_edep > window.highestEdep) {
          window.startTime = current_time;
          fWindowExpiry.push({window.hash, window.startTime + fTimeWindow});
          window.highestEdep = current_edep;
        }
        break;
      default:
        Fatal("Unknown time window policy");
      }
    }

    // Add the current digi to the window.
    window.fillerIn->Fill(iter.fIndex);

    iter++;
  }
  fTimeSorter->MarkOutputAsProcessed();
}

void GateDigitizerPileupActor::ProcessPileupWindow(PileupWindow &window) {
  // This function simulates pile-up by combining the digis in the given window

  std::optional<double> highest_edep{};
  double total_edep = 0.0;
  std::optional<size_t> first_index;
  size_t highest_edep_index = 0;
  size_t last_index = 0;
  G4ThreeVector weighted_position;
  G4ThreeVector highest_edep_position;

  if (window.digis->GetSize() == 0) {
    return;
  }

  // Iterate over all digis in the window from the beginning.
  auto &iter = window.digiIter;
  iter.GoToBegin();
  while (!iter.IsAtEnd()) {
    const auto current_edep = *fPileupWindowEdep;
    const auto current_pos = *fPileupWindowPos;
    // Remember the index of the first digi.
    if (!first_index) {
      first_index = iter.fIndex;
    }
    // Remember the index of the last digi.
    last_index = iter.fIndex;
    // Remember the value and index of the highest deposited energy so far.
    if (!highest_edep.has_value() || current_edep > highest_edep.value()) {
      highest_edep = current_edep;
      highest_edep_index = iter.fIndex;
      highest_edep_position = current_pos;
    }
    // Accumulate all deposited energy values.
    total_edep += current_edep;

    if (fPositionAttributePolicy ==
        PositionAttributePolicy::EnergyWeightedCentroid) {
      // Accumulate the energy-weighted position.
      weighted_position += current_pos * current_edep;
    }
    iter++;
  }
  if (fPositionAttributePolicy ==
      PositionAttributePolicy::EnergyWeightedCentroid) {
    weighted_position /= total_edep;
  }

  // Get output attribute pointer.
  auto outputEdepAttribute =
      fOutputDigiCollection->GetDigiAttribute("TotalEnergyDeposit");
  auto outputPosAttribute =
      fOutputDigiCollection->GetDigiAttribute("PostPosition");

  // The resulting pile-up digi gets:
  // - the total edep value.
  outputEdepAttribute->FillDValue(total_edep);
  // - the position according to the position attribute policy.
  if (fPositionAttributePolicy == PositionAttributePolicy::EnergyWinner) {
    outputPosAttribute->Fill3Value(highest_edep_position);
  } else if (fPositionAttributePolicy ==
             PositionAttributePolicy::EnergyWeightedCentroid) {
    outputPosAttribute->Fill3Value(weighted_position);
  }
  // All the other attribute values are according to the attribute policy.
  if (fAttributePolicy == AttributePolicy::First) {
    window.fillerOut->Fill(*first_index);
  } else if (fAttributePolicy == AttributePolicy::EnergyWinner) {
    window.fillerOut->Fill(highest_edep_index);
  } else if (fAttributePolicy == AttributePolicy::Last) {
    window.fillerOut->Fill(last_index);
  }
  // Remove all processed digis from the window.
  window.digis->Clear();
}

void GateDigitizerPileupActor::ProcessPileupWindows(double currentTime) {

  // Process the expiry items for which the expiry time is before currentTime.
  while (fWindowExpiry.size() > 0 &&
         currentTime > fWindowExpiry.front().expiryTime) {
    auto &window = fVolumePileupWindows.at(fWindowExpiry.front().volumeHash);
    // Check again whether the window is actually expired, because its expiry
    // time may have been updated in a later expiry item.
    if (currentTime > window.startTime + fTimeWindow) {
      ProcessPileupWindow(window);
    }
    fWindowExpiry.pop();
  }
}