/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#include "GamHelpers.h"
#include <G4Threading.hh>

const int LogLevel_RUN = 20;
const int LogLevel_EVENT = 50;

void Fatal(std::string s) {
    std::cout << "ERROR in GAM_G4 " << s << std::endl;
    exit(0);
}
