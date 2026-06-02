/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#include "GateDigitizerDeadTimeActor.h"
#include "../GateHelpersDict.h"
#include "GateHelpersDigitizer.h"
#include <memory>

GateDigitizerDeadTimeActor::GateDigitizerDeadTimeActor(py::dict &user_info)
    : GateVDigitizerWithOutputActor(user_info, true) {
  fActions.insert("EndOfEventAction");
  fActions.insert("EndOfRunAction");
}

GateDigitizerDeadTimeActor::~GateDigitizerDeadTimeActor() = default;

void GateDigitizerDeadTimeActor::InitializeUserInfo(py::dict &user_info) {

  GateVDigitizerWithOutputActor::InitializeUserInfo(user_info);
  if (py::len(user_info) > 0 && user_info.contains("dead_time")) {
    fDeadTime = DictGetDouble(user_info, "dead_time"); // nanoseconds
  }
  if (py::len(user_info) > 0 && user_info.contains("policy")) {
    const auto policy_str = DictGetStr(user_info, "policy");
    if (policy_str == "NonParalyzable") {
      fPolicy = DeadTimePolicy::NonParalyzable;
    } else if (policy_str == "Paralyzable") {
      fPolicy = DeadTimePolicy::Paralyzable;
    } else {
      Fatal("Unknown dead time policy '" + policy_str + "'");
    }
  }

  if (py::len(user_info) > 0 && user_info.contains("sorting_time")) {
    fSortingTime = DictGetDouble(user_info, "sorting_time"); // nanoseconds
  }
  fGroupVolumeDepth = -1;
  fInputDigiCollectionName = DictGetStr(user_info, "input_digi_collection");
}

void GateDigitizerDeadTimeActor::BeginOfRunActionMasterThread(int run_id) {

  fTimeSorter = std::make_unique<GateTimeSorter>(fOutputDigiCollectionName);
  fTimeSorter->Init(fInputDigiCollection);
  fTimeSorter->SetSortingWindow(fSortingTime);
  fTimeSorter->SetMaxSize(fClearEveryNEvents);

  auto &outputIter = fTimeSorter->OutputIterator();
  outputIter.TrackAttribute("GlobalTime", &fTimeSorterOutputTime);
  outputIter.TrackAttribute("PreStepUniqueVolumeID", &fTimeSorterOutputVolID);

  fillerOut = std::make_unique<GateDigiAttributesFiller>(
      fTimeSorter->OutputCollection(), fOutputDigiCollection,
      fTimeSorter->OutputCollection()->GetDigiAttributeNames());

  fVolumeEndOfDeadTimeInterval.clear();
}

void GateDigitizerDeadTimeActor::SetGroupVolumeDepth(const int depth) {
  fGroupVolumeDepth = depth;
}

void GateDigitizerDeadTimeActor::DigitInitialize(
    const std::vector<std::string> &attributes_not_in_filler) {

  auto a = attributes_not_in_filler;
  GateVDigitizerWithOutputActor::DigitInitialize(a);

  fOutputDigiCollection->RootInitializeTupleForWorker();
}

void GateDigitizerDeadTimeActor::EndOfEventAction(const G4Event *) {

  fTimeSorter->OnEndOfEventAction([this]() { ProcessTimeSortedDigis(); });
}

void GateDigitizerDeadTimeActor::EndOfRunAction(const G4Run *) {

  fTimeSorter->OnEndOfRunAction(
      [this]() { fOutputDigiCollection->FillToRootIfNeeded(true); },
      [this]() { ProcessTimeSortedDigis(); });
}

void GateDigitizerDeadTimeActor::ProcessTimeSortedDigis() {

  auto &iter = fTimeSorter->OutputIterator();
  iter.GoToBegin();
  while (!iter.IsAtEnd()) {

    const auto volHash =
        fTimeSorterOutputVolID->get()->GetIdUpToDepthAsHash(fGroupVolumeDepth);
    std::optional<double> endTime{};
    auto it = fVolumeEndOfDeadTimeInterval.find(volHash);
    if (it != fVolumeEndOfDeadTimeInterval.end()) {
      endTime = it->second;
    }

    const auto currentTime = *fTimeSorterOutputTime;
    if (!endTime.has_value() || currentTime > *endTime) {
      // Digi goes to the output.
      fillerOut->Fill(iter.fIndex);
      // Update end of dead time interval.
      fVolumeEndOfDeadTimeInterval[volHash] = currentTime + fDeadTime;
    } else {
      // Digi is dropped because it arrived during a dead time interval.
      if (fPolicy == DeadTimePolicy::NonParalyzable) {
        // End of dead time interval does not change.
      } else if (fPolicy == DeadTimePolicy::Paralyzable) {
        // End of dead time interval is updated.
        fVolumeEndOfDeadTimeInterval[volHash] = currentTime + fDeadTime;
      } else {
        Fatal("Unknown dead time policy");
      }
    }

    iter++;
  }
  fTimeSorter->MarkOutputAsProcessed();
}
