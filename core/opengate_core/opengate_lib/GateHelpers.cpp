/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#include "GateHelpers.h"
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
