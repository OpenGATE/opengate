/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#ifndef GamSignalHandler_h
#define GamSignalHandler_h

#include <csignal>
#include "GamHelpers.h"


void QuitSignalHandler(int) {
    std::cout << "--- Simulation interrupted by user (Control-C) ---" << std::endl;
    exit(0);
}

G4int InstallSignalHandler() {
    if (signal(SIGINT, QuitSignalHandler) == SIG_ERR) {
        Fatal("Error while installing QuitSignalHandler");
    }
}


#endif // GamSignalHandler_h
