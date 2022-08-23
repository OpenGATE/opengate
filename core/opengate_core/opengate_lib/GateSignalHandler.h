/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#ifndef GateSignalHandler_h
#define GateSignalHandler_h

#include "GateHelpers.h"
#include <csignal>

void QuitSignalHandler(int) {
  std::cout << "--- Simulation interrupted by user (Control-C) ---"
            << std::endl;
  exit(0);
}

void InstallSignalHandler() {
  if (signal(SIGINT, QuitSignalHandler) == SIG_ERR) {
    Fatal("Error while installing QuitSignalHandler");
  }
}

#endif // GateSignalHandler_h
