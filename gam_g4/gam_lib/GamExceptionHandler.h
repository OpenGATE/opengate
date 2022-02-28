/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#ifndef GamExceptionHandler_h
#define GamExceptionHandler_h

#include <G4VExceptionHandler.hh>


class GamExceptionHandler : public G4VExceptionHandler {
public:
    GamExceptionHandler();
    virtual ~GamExceptionHandler();
    virtual G4bool Notify(const char *originOfException,
                          const char *exceptionCode,
                          G4ExceptionSeverity severity,
                          const char *description);
};

#endif // GamExceptionHandler_h
