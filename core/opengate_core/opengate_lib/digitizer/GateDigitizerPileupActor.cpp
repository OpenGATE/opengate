/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#include "GateDigitizerPileupActor.h"
#include "../GateHelpersDict.h"

GateDigitizerPileupActor::GateDigitizerPileupActor(py::dict &user_info)
    : GateVDigitizerWithOutputActor(user_info, false) {
  fActions.insert("EndOfEventAction");
  fActions.insert("EndOfRunAction");
}

GateDigitizerPileupActor::~GateDigitizerPileupActor() = default;

void GateDigitizerPileupActor::InitializeUserInfo(py::dict &user_info) {
  GateVDigitizerWithOutputActor::InitializeUserInfo(user_info);

  // Get time window parameter in ns.
  fTimeWindow = 0.0; // default value, no pile-up
  if (py::len(user_info) > 0 && user_info.contains("time_window")) {
    fTimeWindow = DictGetDouble(user_info, "time_window");
  }
  fGroupVolumeDepth = -1;
}

void GateDigitizerPileupActor::SetGroupVolumeDepth(const int depth) {
  fGroupVolumeDepth = depth;
}

void GateDigitizerPileupActor::DigitInitialize(
    const std::vector<std::string> &attributes_not_in_filler) {
  // We handle all attributes explicitly by storing their values,
  // because we need to keep singles across consecutive events.
  auto a = attributes_not_in_filler;
  for (const auto &att_name : fInputDigiCollection->GetDigiAttributeNames()) {
    a.push_back(att_name);
  }

  GateVDigitizerWithOutputActor::DigitInitialize(a);

  // Get output attribute pointers
  fOutputEdepAttribute =
      fOutputDigiCollection->GetDigiAttribute("TotalEnergyDeposit");
  fOutputGlobalTimeAttribute =
      fOutputDigiCollection->GetDigiAttribute("GlobalTime");
  fOutputVolumeIDAttribute =
      fOutputDigiCollection->GetDigiAttribute("PreStepUniqueVolumeID");

  // Set up pointers to track specific attributes
  auto &lr = fThreadLocalVDigitizerData.Get();
  auto &l = fThreadLocalData.Get();

  lr.fInputIter = fInputDigiCollection->NewIterator();
  lr.fInputIter.TrackAttribute("TotalEnergyDeposit", &l.edep);
  lr.fInputIter.TrackAttribute("GlobalTime", &l.time);
  lr.fInputIter.TrackAttribute("PreStepUniqueVolumeID", &l.volID);
}

void GateDigitizerPileupActor::BeginOfRunAction(const G4Run *run) {
  GateVDigitizerWithOutputActor::BeginOfRunAction(run);
}

void GateDigitizerPileupActor::StoreAttributeValues(
    threadLocalT::PileupGroup &group, size_t index) {
  // Clear previous values
  group.stored_attributes.clear();

  // Store values from all attributes in the input collection
  for (auto *att : fInputDigiCollection->GetDigiAttributes()) {
    auto name = att->GetDigiAttributeName();
    auto type = att->GetDigiAttributeType();

    // Skip the attributes we handle explicitly
    if (name == "TotalEnergyDeposit" || name == "GlobalTime" ||
        name == "PreStepUniqueVolumeID") {
      continue;
    }

    // Store value based on type
    switch (type) {
    case 'D': // double
      group.stored_attributes[name] = att->GetDValues()[index];
      break;
    case 'I': // int
      group.stored_attributes[name] = att->GetIValues()[index];
      break;
    case 'L': // int64_t
      group.stored_attributes[name] = att->GetLValues()[index];
      break;
    case 'S': // string
      group.stored_attributes[name] = att->GetSValues()[index];
      break;
    case '3': // G4ThreeVector
      group.stored_attributes[name] = att->Get3Values()[index];
      break;
    case 'U': // GateUniqueVolumeID::Pointer
      group.stored_attributes[name] = att->GetUValues()[index];
      break;
    }
  }
}

void GateDigitizerPileupActor::EndOfEventAction(const G4Event *) {
  ProcessPileup();

  // Create output singles from piled-up groups of input singles.

  auto &l = fThreadLocalData.Get();

  for (auto &[volume_id, groups] : l.volume_groups) {
    if (!groups.empty()) {
      // Handle all groups, except the last one, because the last group may
      // still get contributions from upcoming events.
      for (auto it = groups.begin(); it != std::prev(groups.end()); ++it) {
        FillAttributeValues(*it);
      }
      groups.erase(groups.begin(), std::prev(groups.end()));
    }
  }
}

void GateDigitizerPileupActor::ProcessPileup() {

  auto &lr = fThreadLocalVDigitizerData.Get();
  auto &l = fThreadLocalData.Get();
  auto &iter = lr.fInputIter;

  iter.GoToBegin();
  while (!iter.IsAtEnd()) {

    const auto current_time = *l.time;
    const auto current_edep = *l.edep;
    const auto current_vol =
        l.volID->get()->GetIdUpToDepthAsHash(fGroupVolumeDepth);
    const auto current_index = iter.fIndex;

    bool added_to_existing_group = false;
    auto &groups = l.volume_groups[current_vol];
    if (groups.size() > 0) {
      auto &group = groups.back();
      if (std::abs(current_time - group.first_time) <= fTimeWindow) {
        // Accumulate deposited energy of all singles in the same time window.
        group.total_edep += current_edep;
        // Keep the attributes of the highest energy single.
        if (current_edep > group.highest_edep) {
          group.highest_edep = current_edep;
          group.time = current_time;
          // Store all other attribute values from this single.
          StoreAttributeValues(group, current_index);
        }
        added_to_existing_group = true;
      }
    }

    // If not added to an existing group, create a new group.
    if (!added_to_existing_group) {
      typename threadLocalT::PileupGroup new_group;
      new_group.total_edep = current_edep;
      new_group.highest_edep = current_edep;
      new_group.first_time = current_time;
      new_group.time = current_time;
      new_group.volume_id = *l.volID;
      // Store all other attribute values from this single
      StoreAttributeValues(new_group, current_index);
      groups.push_back(new_group);
    }

    iter++;
  }
}

void GateDigitizerPileupActor::EndOfRunAction(const G4Run *) {

  auto &l = fThreadLocalData.Get();

  // Output any unfinished groups that are still present.
  for (auto &[volume_id, groups] : l.volume_groups) {
    if (!groups.empty()) {
      for (auto &group : groups) {
        FillAttributeValues(group);
      }
      groups.erase(groups.begin(), groups.end());
    }
  }

  // Make sure everything is output into the root file.
  fOutputDigiCollection->FillToRootIfNeeded(true);
}

void GateDigitizerPileupActor::FillAttributeValues(
    const threadLocalT::PileupGroup &group) {

  fOutputEdepAttribute->FillDValue(group.total_edep);
  fOutputGlobalTimeAttribute->FillDValue(group.time);
  fOutputVolumeIDAttribute->FillUValue(group.volume_id);

  // Fill all other stored attributes
  for (const auto &[name, value] : group.stored_attributes) {
    auto *att = fOutputDigiCollection->GetDigiAttribute(name);
    std::visit(
        [att](auto &&arg) {
          using T = std::decay_t<decltype(arg)>;
          if constexpr (std::is_same_v<T, double>) {
            att->FillDValue(arg);
          } else if constexpr (std::is_same_v<T, int>) {
            att->FillIValue(arg);
          } else if constexpr (std::is_same_v<T, int64_t>) {
            att->FillLValue(arg);
          } else if constexpr (std::is_same_v<T, std::string>) {
            att->FillSValue(arg);
          } else if constexpr (std::is_same_v<T, G4ThreeVector>) {
            att->Fill3Value(arg);
          } else if constexpr (std::is_same_v<T, GateUniqueVolumeID::Pointer>) {
            att->FillUValue(arg);
          }
        },
        value);
  }
}