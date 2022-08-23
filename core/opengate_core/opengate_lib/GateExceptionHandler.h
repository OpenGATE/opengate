/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#ifndef GateExceptionHandler_h
#define GateExceptionHandler_h

#include <G4VExceptionHandler.hh>

class GateExceptionHandler : public G4VExceptionHandler {
public:
  GateExceptionHandler();
  virtual ~GateExceptionHandler();
  virtual G4bool Notify(const char *originOfException,
                        const char *exceptionCode, G4ExceptionSeverity severity,
                        const char *description);
};

#endif // GateExceptionHandler_h
