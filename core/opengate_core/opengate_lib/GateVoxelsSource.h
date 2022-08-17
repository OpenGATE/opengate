/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#ifndef GateVoxelsSource_h
#define GateVoxelsSource_h

#include <pybind11/stl.h>
#include "GateGenericSource.h"
#include "GateSingleParticleSource.h"
#include "GateSPSVoxelsPosDistribution.h"

namespace py = pybind11;

class GateVoxelsSource : public GateGenericSource {

public:
    GateVoxelsSource();

    virtual ~GateVoxelsSource();

    virtual void PrepareNextRun();

    GateSPSVoxelsPosDistribution *GetSPSVoxelPosDistribution() { return fVoxelPositionGenerator; }

protected:
    void InitializePosition(py::dict user_info);

    GateSPSVoxelsPosDistribution * fVoxelPositionGenerator;

};

#endif // GateVoxelsSource_h
