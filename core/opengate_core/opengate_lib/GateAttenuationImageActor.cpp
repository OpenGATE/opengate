/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#include "GateAttenuationImageActor.h"
#include "G4SDManager.hh"
#include "GateHelpersDict.h"
#include "GateSourceManager.h"
#include "GateVActor.h"

GateAttenuationImageActor::GateAttenuationImageActor(py::dict &user_info,
                                                     bool MT_ready)
    : GateVActor(user_info, MT_ready) {}

GateAttenuationImageActor::~GateAttenuationImageActor() {}
