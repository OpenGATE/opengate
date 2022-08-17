/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#include "G4ParticleTable.hh"
#include "GateVoxelsSource.h"
#include "GateHelpersDict.h"


GateVoxelsSource::GateVoxelsSource() : GateGenericSource() {
    fVoxelPositionGenerator = new GateSPSVoxelsPosDistribution();
}

GateVoxelsSource::~GateVoxelsSource() {
}

void GateVoxelsSource::PrepareNextRun() {
    GateGenericSource::PrepareNextRun();
    // rotation and translation to apply, according to mother volume
    fVoxelPositionGenerator->fGlobalRotation = fGlobalRotation;
    fVoxelPositionGenerator->fGlobalTranslation = fGlobalTranslation;

    // the direction is 'isotropic' so we don't care about rotating the direction.
}

void GateVoxelsSource::InitializePosition(py::dict) {
    fSPS->SetPosGenerator(fVoxelPositionGenerator);
    // we set a fake value (not used)
    fVoxelPositionGenerator->SetPosDisType("Point");
}

