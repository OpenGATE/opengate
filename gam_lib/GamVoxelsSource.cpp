/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#include "G4ParticleTable.hh"
#include "G4RandomTools.hh"
#include "G4IonTable.hh"
#include "G4UnitsTable.hh"
#include "GamVoxelsSource.h"
#include "GamHelpers.h"
#include "GamDictHelpers.h"
#include "GamSPSVoxelsPosDistribution.h"


GamVoxelsSource::GamVoxelsSource() : GamGenericSource() {
    DDD("constructor GamVoxelsSource");
    fVoxelPositionGenerator = new GamSPSVoxelsPosDistribution();
}

GamVoxelsSource::~GamVoxelsSource() {
}

void GamVoxelsSource::InitializePosition(py::dict user_info) {
    DDD("init position voxel source");
    fSPS->SetPosGenerator(fVoxelPositionGenerator);
    fVoxelPositionGenerator->SetPosDisType("Point"); // FIXME
    DDD(fVoxelPositionGenerator);
}

