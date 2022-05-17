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
    fStart = DictGetG4ThreeVector(user_info, "start");
    auto repeat = DictGetG4ThreeVector(user_info, "linear_repeat");
    fTranslation = DictGetG4ThreeVector(user_info, "translation");
    fOffset = DictGetG4ThreeVector(user_info, "offset");
    fNbOffset = DictGetInt(user_info, "offset_nb");
    fSx = int(repeat[0]);
    fSy = int(repeat[1]);
    fSz = int(repeat[2]);
    auto m = fSx * fSy * fSz;
    fTranslations.resize(m);
    int no = 0;
    // Exact same order and numbering than the "repeater" counterpart in Python side
    for (auto of = 0; of < fNbOffset; of++) {
        for (auto i = 0; i < fSx; i++) {
            for (auto j = 0; j < fSy; j++) {
                for (auto k = 0; k < fSz; k++) {
                    G4ThreeVector t(fStart[0] + i * fTranslation[0] + of * fOffset[0],
                                    fStart[1] + j * fTranslation[1] + of * fOffset[1],
                                    fStart[2] + k * fTranslation[2] + of * fOffset[2]);
                    fTranslations[no] = t;
                    no++;
                }
            }
        }
    }

}

void GamRepeatParameterisation::ComputeTransformation(const G4int no,
                                                      G4VPhysicalVolume *currentPV) const {
    currentPV->SetTranslation(fTranslations[no]);
}
