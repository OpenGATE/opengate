/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#ifndef GateRepeatParameterisation_h
#define GateRepeatParameterisation_h

#include "GateHelpers.h"
#include "G4VPVParameterisation.hh"
#include "G4NistManager.hh"
#include "G4VPhysicalVolume.hh"
#include "G4VTouchable.hh"

class GateRepeatParameterisation : public G4VPVParameterisation {

public:

    void SetUserInfo(py::dict &user_info);

    virtual void ComputeTransformation(const G4int no, G4VPhysicalVolume *currentPV) const;

    G4ThreeVector fStart;
    G4ThreeVector fTranslation;
    G4ThreeVector fOffset;
    int fNbOffset;
    int fSx;
    int fSy;
    int fSz;
    int fStride;
    int fTotal;
    std::vector<G4ThreeVector> fTranslations;
};

#endif // GateRepeatParameterisation_h
