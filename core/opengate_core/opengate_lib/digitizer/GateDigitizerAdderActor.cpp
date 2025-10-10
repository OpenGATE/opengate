/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#include "GateDigitizerAdderActor.h"
#include "../GateHelpersDict.h"
#include "../GateUserTrackInformation.h"
#include "GateDigiAdderInVolume.h"
#include "GateDigiCollectionManager.h"
#include <functional>
#include <sstream>

GateDigitizerAdderActor::GateDigitizerAdderActor(py::dict &user_info)
    : GateVDigitizerWithOutputActor(user_info, true) {
  // actions (in addition to the ones in GateVDigitizerWithOutputActor)
  fActions.insert("EndOfEventAction");
  fGroupVolumeDepth = -1;
  fPolicy = AdderPolicy::EnergyWinnerPosition;
  fTimeDifferenceFlag = false;
  fNumberOfHitsFlag = false;
  fWeightsAreUsedFlag = false;
}

GateDigitizerAdderActor::~GateDigitizerAdderActor() = default;

void GateDigitizerAdderActor::InitializeUserInfo(py::dict &user_info) {
  GateVDigitizerWithOutputActor::InitializeUserInfo(user_info);
  // policy
  fPolicy = AdderPolicy::Error;
  const auto policy = DictGetStr(user_info, "policy");
  if (policy == "EnergyWinnerPosition")
    fPolicy = AdderPolicy::EnergyWinnerPosition;
  else if (policy == "EnergyWeightedCentroidPosition")
    fPolicy = AdderPolicy::EnergyWeightedCentroidPosition;
  if (fPolicy == AdderPolicy::Error) {
    std::ostringstream oss;
    oss << "Error in GateDigitizerAdderActor: unknown policy. Must be "
           "EnergyWinnerPosition or EnergyWeightedCentroidPosition"
        << " while '" << policy << "' is read.";
    Fatal(oss.str());
  }

  // option
  fTimeDifferenceFlag = DictGetBool(user_info, "time_difference");
  fNumberOfHitsFlag = DictGetBool(user_info, "number_of_hits");

  // init
  fGroupVolumeDepth = -1;
}

void GateDigitizerAdderActor::SetGroupVolumeDepth(const int depth) {
  fGroupVolumeDepth = depth;
}

void GateDigitizerAdderActor::StartSimulationAction() {
  // Init output (do not initialize root because we may add some options)
  fInitializeRootTupleForMasterFlag = false;
  GateVDigitizerWithOutputActor::StartSimulationAction();
  fInitializeRootTupleForMasterFlag = true;

  // add the optional attributes if needed
  if (fTimeDifferenceFlag) {
    auto *att = new GateTDigiAttribute<double>("TimeDifference");
    fOutputDigiCollection->InitDigiAttribute(att);
  }
  if (fNumberOfHitsFlag) {
    auto *att = new GateTDigiAttribute<double>("NumberOfHits");
    fOutputDigiCollection->InitDigiAttribute(att);
  }
  fOutputDigiCollection->RootInitializeTupleForMaster();

  // check required attributes
  CheckRequiredAttribute(fInputDigiCollection, "TotalEnergyDeposit");
  CheckRequiredAttribute(fInputDigiCollection, "PostPosition");
  CheckRequiredAttribute(fInputDigiCollection, "PreStepUniqueVolumeID");
  CheckRequiredAttribute(fInputDigiCollection, "GlobalTime");
}

void GateDigitizerAdderActor::DigitInitialize(
    const std::vector<std::string> &attributes_not_in_filler) {
  // remove the attributes that will be computed here
  std::vector<std::string> att = attributes_not_in_filler;
  att.emplace_back("TotalEnergyDeposit");
  att.emplace_back("PostPosition");
  att.emplace_back("GlobalTime");
  if (fTimeDifferenceFlag)
    att.emplace_back("TimeDifference");
  if (fNumberOfHitsFlag)
    att.emplace_back("NumberOfHits");
  GateVDigitizerWithOutputActor::DigitInitialize(att);

  // Get thread local variables
  auto &l = fThreadLocalData.Get();

  // set output pointers to the attributes needed for computation
  fOutputEdepAttribute =
      fOutputDigiCollection->GetDigiAttribute("TotalEnergyDeposit");
  fOutputPosAttribute = fOutputDigiCollection->GetDigiAttribute("PostPosition");
  fOutputGlobalTimeAttribute =
      fOutputDigiCollection->GetDigiAttribute("GlobalTime");
  if (fTimeDifferenceFlag)
    fOutputTimeDifferenceAttribute =
        fOutputDigiCollection->GetDigiAttribute("TimeDifference");
  if (fNumberOfHitsFlag)
    fOutputNumberOfHitsAttribute =
        fOutputDigiCollection->GetDigiAttribute("NumberOfHits");

  // set input pointers to the attributes needed for computation
  auto &lr = fThreadLocalVDigitizerData.Get();
  lr.fInputIter = fInputDigiCollection->NewIterator();
  lr.fInputIter.TrackAttribute("TotalEnergyDeposit", &l.edep);
  lr.fInputIter.TrackAttribute("PostPosition", &l.pos);
  lr.fInputIter.TrackAttribute("PreStepUniqueVolumeID", &l.volID);
  lr.fInputIter.TrackAttribute("GlobalTime", &l.time);

  // Weights?
  // If yes, we consider grouping for tracks with the exact same weights
  if (fInputDigiCollection->IsDigiAttributeExists("Weight")) {
    lr.fInputIter.TrackAttribute("Weight", &l.weight);
    fWeightsAreUsedFlag = true;
  }
}

void GateDigitizerAdderActor::EndOfEventAction(const G4Event *event) {
  // loop on all hits to group per volume ID
  auto &lr = fThreadLocalVDigitizerData.Get();
  auto &iter = lr.fInputIter;
  iter.GoToBegin();

  while (!iter.IsAtEnd()) {
    AddDigiPerVolume();
    iter++;
  }

  // create the output hits collection for grouped hits
  auto &l = fThreadLocalData.Get();

  for (auto &h : l.fMapOfDigiInVolume) {
    const auto &hit = h.second;
    // terminate the merge
    hit->Terminate();
    // Don't store anything if edep is zero
    if (hit->fFinalEdep > 0) {
      fOutputEdepAttribute->FillDValue(hit->fFinalEdep);
      fOutputPosAttribute->Fill3Value(hit->fFinalPosition);
      fOutputGlobalTimeAttribute->FillDValue(hit->fFinalTime);
      if (fTimeDifferenceFlag)
        fOutputTimeDifferenceAttribute->FillDValue(hit->fDifferenceTime);
      if (fNumberOfHitsFlag)
        fOutputNumberOfHitsAttribute->FillDValue(hit->fNumberOfHits);
      lr.fDigiAttributeFiller->Fill(hit->fFinalIndex);
    }
    // Clean up the allocated GateDigiAdderInVolume object
    delete hit;
  }

  // reset the structure of hits
  l.fMapOfDigiInVolume.clear();
}

void GateDigitizerAdderActor::AddDigiPerVolume() const {
  auto &l = fThreadLocalData.Get();
  auto &lr = fThreadLocalVDigitizerData.Get();
  const auto &i = lr.fInputIter.fIndex;

  if (*l.edep == 0)
    return;

  // Create an efficient key for grouping hits.
  // This key combines the volume ID and, if needed, the track weight.
  DigiKey key{};

  // 1. Get the cached hash of the volume ID string based on the required depth.
  // This function handles caching internally
  key.volumeID = l.volID->get()->GetIdUpToDepthAsHash(fGroupVolumeDepth);

  // 2. Get the weight. If VRT is used, we must group only hits with the
  // exact same weight. To do this safely with floating-point numbers,
  // we use their underlying bit representation as part of the key.
  key.weightBits = 0; // Default value if weights are not used
  if (fWeightsAreUsedFlag) {
    // this copies the bit pattern of the double into the uint64_t.
    std::memcpy(&key.weightBits, l.weight, sizeof(double));
  }

  // Find or create an entry in the map for this unique key.
  if (l.fMapOfDigiInVolume.find(key) == l.fMapOfDigiInVolume.end()) {
    // If no entry exists, create a new one.
    l.fMapOfDigiInVolume[key] = new GateDigiAdderInVolume(
        fPolicy, fTimeDifferenceFlag, fNumberOfHitsFlag);
  }

  // Update the adder (either newly created or pre-existing).
  l.fMapOfDigiInVolume[key]->Update(i, *l.edep, *l.pos, *l.time);
}
