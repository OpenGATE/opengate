/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#include "GamHelpers.h"
#include "G4Threading.hh"

void Fatal(const std::string s) {
    std::cout << "ERROR in GAM_G4 " << s << std::endl;
    exit(0);
}

int GetThreadIndex() {
    /*
     Warning, if no MT TreadId is -1. So the index = 0 is return
     */
    auto i = 0;
    if (G4Threading::IsWorkerThread()) i = G4Threading::G4GetThreadId();
    return i;
}
