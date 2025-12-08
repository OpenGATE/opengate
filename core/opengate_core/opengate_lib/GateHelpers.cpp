/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#include "GateHelpers.h"

#include "G4GammaGeneralProcess.hh"
#include <G4VProcess.hh>
#if USE_VISU == 1
#include <QApplication>
#include <QWidget>
#endif
#include <stdexcept>

const int LogLevel_RUN = 20;
const int LogLevel_EVENT = 50;
G4Mutex DebugMutex = G4MUTEX_INITIALIZER;

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
  const auto p = step->GetPostStepPoint()->GetProcessDefinedStep();
  std::string pp = "";
  if (p != nullptr) {
    pp = p->GetProcessName();
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

int createTestQtWindow() {
#if USE_VISU == 1
  int argc = 1;
  char *argv[] = {(char *)"minimal", nullptr};
  QApplication app(argc, argv);

  QWidget window;
  window.resize(320, 240);
  window.setWindowTitle("Minimal Qt Example");
  window.show();

  return app.exec();
#else
  std::cerr << "Qt is not available in this build of OpenGate." << std::endl;
  return -1;
#endif
}
