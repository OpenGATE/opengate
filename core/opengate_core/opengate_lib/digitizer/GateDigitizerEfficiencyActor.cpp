/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#include "GateDigitizerEfficiencyActor.h"
#include "../GateHelpersDict.h"
#include <Randomize.hh>

GateDigitizerEfficiencyActor::GateDigitizerEfficiencyActor(py::dict &user_info)
    : GateVDigitizerWithOutputActor(user_info, true) {

  // actions
  fActions.insert("EndOfEventAction");
}

void GateDigitizerEfficiencyActor::InitializeUserInfo(py::dict &user_info) {
  GateVDigitizerWithOutputActor::InitializeUserInfo(user_info);
  // efficiency method
  fEfficiency = DictGetDouble(user_info, "efficiency");
}

void GateDigitizerEfficiencyActor::DigitInitialize(
    const std::vector<std::string> &attributes_not_in_filler) {
  GateVDigitizerWithOutputActor::DigitInitialize(attributes_not_in_filler);
}

void GateDigitizerEfficiencyActor::EndOfEventAction(
    const G4Event * /*unused*/) {
  // loop on all digi of this events
  auto &lr = fThreadLocalVDigitizerData.Get();
  auto &iter = lr.fInputIter;
  // no digi in this event: nothing to do
  if (!iter.GoToBegin())
    return;
  while (!iter.IsAtEnd()) {
    if (G4UniformRand() < fEfficiency) {
      auto &i = lr.fInputIter.fIndex;
      lr.fDigiAttributeFiller->Fill(i);
    }
    iter++;
  }
}
