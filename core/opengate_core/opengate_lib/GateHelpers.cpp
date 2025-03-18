/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#include "GateHelpers.h"
#include <G4Threading.hh>
#include <stdexcept>

const int LogLevel_RUN = 20;
const int LogLevel_EVENT = 50;

void Fatal(std::string s) {
  std::cout << "ERROR in OPENGATE " << s << std::endl;
  exit(-1);
}

void FatalKeyError(std::string s) {
  throw py::key_error("Error in the Opengate library (C++): " + s);
}
