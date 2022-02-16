/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#include "G4UnitsTable.hh"
#include "GamRepeatParameterisation.h"
#include "GamHelpersDict.h"

void GamRepeatParameterisation::SetUserInfo(py::dict &user_info) {
    fStart = Dict3DVector(user_info, "start");
    auto repeat = Dict3DVector(user_info, "linear_repeat");
    fTranslation = Dict3DVector(user_info, "translation");
    fOffset = Dict3DVector(user_info, "offset");
    fNbOffset = DictInt(user_info, "offset_nb");
    fSx = int(repeat[0]);
    fSy = int(repeat[1]);
    fSz = int(repeat[2]);
    fStride = fSx * fSy;
    fTotal = fStride * fSz;
    auto m = fTotal * fNbOffset;
    fTranslations.resize(m);
    for (auto no = 0; no < m; no++) {
        int of = no / fTotal;
        int rof = no % fTotal;
        int k = rof / fStride;
        int r = rof % fStride;
        int j = r / fSx;
        int i = r % fSx;
        G4ThreeVector t(fStart[0] + i * fTranslation[0] + of * fOffset[0],
                        fStart[1] + j * fTranslation[1] + of * fOffset[1],
                        fStart[2] + k * fTranslation[2] + of * fOffset[2]);
        fTranslations[no] = t;
    }
}

void GamRepeatParameterisation::ComputeTransformation(const G4int no,
                                                      G4VPhysicalVolume *currentPV) const {
    currentPV->SetTranslation(fTranslations[no]);
}
