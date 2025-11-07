/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#ifndef GateAttenuationImageActor_h
#define GateAttenuationImageActor_h

#include "GateVActor.h"
#include <functional>
#include <pybind11/stl.h>

namespace py = pybind11;

class GateSourceManager;

class GateAttenuationImageActor : public GateVActor {

public:
  explicit GateAttenuationImageActor(py::dict &user_info,
                                     bool MT_ready = false);

  ~GateAttenuationImageActor() override;
};

#endif // GateAttenuationImageActor_h
