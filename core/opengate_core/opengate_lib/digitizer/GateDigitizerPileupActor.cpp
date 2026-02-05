/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#include "GateDigitizerPileupActor.h"
#include "../GateHelpersDict.h"
#include "GateDigiCollectionManager.h"
#include "GateHelpersDigitizer.h"
#include <memory>

GateDigitizerPileupActor::GateDigitizerPileupActor(py::dict &user_info)
    : GateVDigitizerWithOutputActor(user_info, false) {
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

  // Get output attribute pointer
  fOutputTimeAttribute = fOutputDigiCollection->GetDigiAttribute("GlobalTime");
  fOutputEdepAttribute =
      fOutputDigiCollection->GetDigiAttribute("TotalEnergyDeposit");
  fOutputPosAttribute = fOutputDigiCollection->GetDigiAttribute("PostPosition");

  // Set up pointers to track specific attributes
  auto &lr = fThreadLocalVDigitizerData.Get();
  auto &l = fThreadLocalData.Get();

  l.fTimeSorter.Init(fInputDigiCollection);
  l.fTimeSorter.OutputIterator().TrackAttribute("GlobalTime", &l.time);
  l.fTimeSorter.OutputIterator().TrackAttribute("TotalEnergyDeposit", &l.edep);
  l.fTimeSorter.OutputIterator().TrackAttribute("PreStepUniqueVolumeID",
                                                &l.volID);
  l.fTimeSorter.SetSortingWindow(fSortingTime);
  l.fTimeSorter.SetMaxSize(fClearEveryNEvents);
}

void GateDigitizerPileupActor::EndOfEventAction(const G4Event *) {
  auto &l = fThreadLocalData.Get();
  l.fTimeSorter.Process();
  ProcessTimeSortedDigis();
}

void GateDigitizerPileupActor::EndOfRunAction(const G4Run *) {
  auto &l = fThreadLocalData.Get();
  l.fTimeSorter.Flush();
  ProcessTimeSortedDigis();
  for (auto &[_vol_hash, window] : l.fVolumePileupWindows) {
    ProcessPileupWindow(window);
  }
  // Make sure everything is output into the root file.
  fOutputDigiCollection->FillToRootIfNeeded(true);
}

GateDigitizerPileupActor::PileupWindow &
GateDigitizerPileupActor::GetPileupWindowForCurrentVolume(
    GateUniqueVolumeID::Pointer *volume,
    std::map<uint64_t, PileupWindow> &windows) {
  // This function looks up the PileupWindow object for the given volume. If it
  // does not yet exist for the volume, it creates a PileupWindow.

  const auto vol_hash = volume->get()->GetIdUpToDepthAsHash(fGroupVolumeDepth);

  // Look up the window based on volume hash
  auto it = windows.find(vol_hash);
  if (it != windows.end()) {
    // Return a reference to the existing PileupWindow object for the volume.
    return it->second;
  } else {
    // A PileupWindow object does not yet exist for this volume: create one.
    PileupWindow window;
    const auto vol_id = volume->get()->GetIdUpToDepth(fGroupVolumeDepth);
    auto &l = fThreadLocalData.Get();
    // Create a GateDigiCollection for this volume, as a temporary storage for
    // digis that belong to the same time window (the name must be unique).
    window.digis = GateDigiCollectionManager::GetInstance()->NewDigiCollection(
        GetName() + "_" + vol_id);
    window.digis->InitDigiAttributesFromCopy(fInputDigiCollection);
    // Create an iterator to be used when digis will be combined into one digi,
    // due to pile-up.
    window.digiIter = window.digis->NewIterator();
    window.digiIter.TrackAttribute("TotalEnergyDeposit", &l.edep);
    window.digiIter.TrackAttribute("PostPosition", &l.pos);
    // Create a filler to copy all digi attributes from the sorted collection
    // into the collection of the window.
    window.fillerIn = l.fTimeSorter.CreateFiller(window.digis);
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
  auto &l = fThreadLocalData.Get();
  auto &iter = l.fTimeSorter.OutputIterator();
  iter.GoToBegin();
  while (!iter.IsAtEnd()) {
    // Look up or create the pile-up window object for the volume to which the
    // current digi belongs.
    auto &window =
        GetPileupWindowForCurrentVolume(l.volID, l.fVolumePileupWindows);

    const auto current_time = *l.time;
    const auto current_edep = *l.edep;
    if (window.digis->GetSize() == 0) {
      // The window has no digis yet: make the window start at the time of the
      // current digi and remember the current edep as highest.
      window.startTime = current_time;
      window.highestEdep = current_edep;
    } else if (current_time - window.startTime > fTimeWindow) {
      // The current digi is beyond the time window: process the digis that are
      // currently in the window, then make the window start at the time of the
      // current digi and remember the current edep as highest.
      ProcessPileupWindow(window);
      window.startTime = current_time;
      window.highestEdep = current_edep;
    }

    if (fTimeWindowPolicy == TimeWindowPolicy::Paralyzable) {
      // In Paralyzable mode, extend the time window to start at the time of
      // the current digi.
      window.startTime = current_time;
    } else if (fTimeWindowPolicy == TimeWindowPolicy::EnergyWinnerParalyzable) {
      // In EnergyWinnerParalyzable mode, extend the time window only if
      // the current digi has higher energy than the highest-energy
      // digi so far.
      if (current_edep > window.highestEdep) {
        window.startTime = current_time;
        window.highestEdep = current_edep;
      }
    }

    // Add the current digi to the window.
    window.fillerIn->Fill(iter.fIndex);

    iter++;
  }
  l.fTimeSorter.MarkOutputAsProcessed();
}

void GateDigitizerPileupActor::ProcessPileupWindow(PileupWindow &window) {
  // This function simulates pile-up by combining the digis in the given window
  // into one digi.
  auto &l = fThreadLocalData.Get();

  std::optional<double> highest_edep{};
  double total_edep = 0.0;
  std::optional<size_t> first_index;
  size_t highest_edep_index = 0;
  size_t last_index = 0;
  G4ThreeVector weighted_position;
  G4ThreeVector highest_edep_position;

  // Iterate over all digis in the window from the beginning.

  window.digiIter.Reset();
  while (!window.digiIter.IsAtEnd()) {
    const auto current_edep = *l.edep;
    const auto current_pos = *l.pos;
    // Remember the index of the first digi.
    if (!first_index) {
      first_index = window.digiIter.fIndex;
    }
    // Remember the index of the last digi.
    last_index = window.digiIter.fIndex;
    // Remember the value and index of the highest deposited energy so far.
    if (!highest_edep.has_value() || current_edep > highest_edep.value()) {
      highest_edep = current_edep;
      highest_edep_index = window.digiIter.fIndex;
      highest_edep_position = current_pos;
    }
    // Accumulate all deposited energy values.
    total_edep += current_edep;

    if (fPositionAttributePolicy ==
        PositionAttributePolicy::EnergyWeightedCentroid) {
      // Accumulate the energy-weighted position.
      weighted_position += current_pos * current_edep;
    }
    window.digiIter++;
  }
  if (fPositionAttributePolicy ==
      PositionAttributePolicy::EnergyWeightedCentroid) {
    weighted_position /= total_edep;
  }

  // The resulting pile-up digi gets:
  // - the total edep value.
  fOutputEdepAttribute->FillDValue(total_edep);
  // - the position according to the position attribute policy.
  if (fPositionAttributePolicy == PositionAttributePolicy::EnergyWinner) {
    fOutputPosAttribute->Fill3Value(highest_edep_position);
  } else if (fPositionAttributePolicy ==
             PositionAttributePolicy::EnergyWeightedCentroid) {
    fOutputPosAttribute->Fill3Value(weighted_position);
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
