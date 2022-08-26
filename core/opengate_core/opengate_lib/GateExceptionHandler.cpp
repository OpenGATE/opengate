/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#include "GateExceptionHandler.h"
#include <iostream>

GateExceptionHandler::GateExceptionHandler() : G4VExceptionHandler() {}

GateExceptionHandler::~GateExceptionHandler() {}

G4bool GateExceptionHandler::Notify(const char *originOfException,
                                    const char *exceptionCode,
                                    G4ExceptionSeverity severity,
                                    const char *description) {
  std::cout << "G4Exception origin: " << originOfException << std::endl;
  std::cout << "G4Exception code: " << exceptionCode << std::endl;
  std::cout << "G4Exception severity: " << severity << std::endl;
  std::cout << description << std::endl;
  return true;
}
