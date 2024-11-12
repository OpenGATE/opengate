/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#include "GateTrackCreatorProcessFilter.h"
#include "G4VProcess.hh"
#include "GateHelpers.h"
#include "GateHelpersDict.h"

void GateTrackCreatorProcessFilter::InitializeUserInput(py::dict &user_info) {
  fProcessName = DictGetStr(user_info, "process_name");
  fPolicy = DictGetStr(user_info, "policy");
}

bool GateTrackCreatorProcessFilter::Accept(G4Step *step) const {
  const auto *p = step->GetTrack()->GetCreatorProcess();
  std::string name = "none";
  if (p != nullptr)
    name = p->GetProcessName();
  if (fPolicy == "accept" && name == fProcessName)
    return true;
  if (fPolicy == "reject" && name != fProcessName)
    return true;
  return false;
}
