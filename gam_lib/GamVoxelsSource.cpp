/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#include "G4ParticleTable.hh"
#include "G4RandomTools.hh"
#include "GamVoxelsSource.h"
#include "GamDictHelpers.h"


GamVoxelsSource::GamVoxelsSource() : GamGenericSource() {
    fVoxelPositionGenerator = new GamSPSVoxelsPosDistribution();
}

GamVoxelsSource::~GamVoxelsSource() {
}

void GamVoxelsSource::InitializePosition(py::dict) {
    fSPS->SetPosGenerator(fVoxelPositionGenerator);
    // we set a fake value (not used)
    fVoxelPositionGenerator->SetPosDisType("Point");
}

