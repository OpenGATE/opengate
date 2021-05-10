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

void GamVoxelsSource::InitializePosition(py::dict puser_info) {
    fSPS->SetPosGenerator(fVoxelPositionGenerator);
    // we set a fake value (not used)
    fVoxelPositionGenerator->SetPosDisType("Point");

    /*
     // disable rotation for the moment
    auto user_info = py::dict(puser_info["position"]);
    auto rotation = DictMatrix(user_info, "rotation");
    CLHEP::HepRep3x3 rr(*rotation.data(0, 0), *rotation.data(0, 1), *rotation.data(0, 2),
                    *rotation.data(1, 0), *rotation.data(1, 1), *rotation.data(1, 2),
                    *rotation.data(2, 0), *rotation.data(2, 1), *rotation.data(2, 2));
    G4RotationMatrix r(rr);
    fVoxelPositionGenerator->SetRotation(r);
    */
}

