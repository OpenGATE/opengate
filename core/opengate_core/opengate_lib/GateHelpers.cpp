/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#include "GateHelpers.h"

#include "G4BiasingProcessInterface.hh"
#include "G4GammaGeneralProcess.hh"
#include <G4VProcess.hh>
#include <stdexcept>

const int LogLevel_RUN = 20;
const int LogLevel_EVENT = 50;

void Fatal(std::string s) {
  std::ostringstream oss;
  oss << "OPENGATE-CORE " << s << std::endl;
  throw std::runtime_error(oss.str());
}

void FatalKeyError(std::string s) {
  throw py::key_error("Error in the Opengate library (C++): " + s);
}

std::string DebugStep(const G4Step *step) {
  std::ostringstream oss;
  auto p = step->GetPostStepPoint()->GetProcessDefinedStep();
  std::string pp = "";
  if (p != nullptr) {
    pp = p->GetProcessName();
    /*try
    {
        const auto *bp =
        static_cast<const G4BiasingProcessInterface *>(p);
        const auto *wrapped_p = bp->GetWrappedProcess();
        const auto *ggp = static_cast<const G4GammaGeneralProcess *>(wrapped_p);
        const auto *proc = ggp->GetSelectedProcess();
        if (proc != nullptr)
        {
            pp = proc->GetProcessName();
        }
    } catch (const std::exception &)
    {
        // continue
    }*/
  }
  oss << "tid= " << step->GetTrack()->GetTrackID() << " "
      << step->GetTrack()->GetCurrentStepNumber() << std::fixed
      << std::setprecision(1)
      << " post= " << step->GetPostStepPoint()->GetPosition()
      << " dir= " << step->GetPostStepPoint()->GetMomentumDirection()
      << std::fixed << std::setprecision(3)
      << " E= " << step->GetPreStepPoint()->GetKineticEnergy()
      << " w=" << step->GetTrack()->GetWeight() << " " << pp;
  return oss.str();
}