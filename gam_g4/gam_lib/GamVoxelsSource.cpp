/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#include "G4ParticleTable.hh"
#include "G4RandomTools.hh"
#include "GamVoxelsSource.h"
#include "GamHelpersDict.h"


GamVoxelsSource::GamVoxelsSource() : GamGenericSource() {
    fVoxelPositionGenerator = new GamSPSVoxelsPosDistribution();
}

GamVoxelsSource::~GamVoxelsSource() {
}

void GamVoxelsSource::PrepareNextRun() {
    GamGenericSource::PrepareNextRun();
    // rotation and translation to apply, according to mother volume
    fVoxelPositionGenerator->fGlobalRotation = fGlobalRotation;
    fVoxelPositionGenerator->fGlobalTranslation = fGlobalTranslation;

    // the direction is 'isotropic' so we don't care about rotating the direction.
}

void GamVoxelsSource::InitializePosition(py::dict) {
    fSPS->SetPosGenerator(fVoxelPositionGenerator);
    // we set a fake value (not used)
    fVoxelPositionGenerator->SetPosDisType("Point");
}

