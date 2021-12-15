/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#ifndef GamHit_h
#define GamHit_h

#include <pybind11/stl.h>
#include "G4VHit.hh"
#include "GamHelpers.h"


class GamHit : public G4VHit {
public:
    GamHit();

    virtual ~GamHit();

};

#endif // GamHit_h
