/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#ifndef GamImageNestedParameterisation_h
#define GamImageNestedParameterisation_h

#include "G4VNestedParameterisation.hh"

class GamImageNestedParameterisation : public G4VNestedParameterisation {

public:

    virtual G4Material *ComputeMaterial(G4VPhysicalVolume *currentVol,
                                        const G4int repNo,
                                        const G4VTouchable *parentTouch = nullptr) {
        std::cout << "I am in ComputeMaterial " << std::endl;
        std::cout << currentVol << std::endl;
        std::cout << repNo << std::endl;
        std::cout << parentTouch << std::endl;
        return nullptr;
    }

    virtual G4int GetNumberOfMaterials() const {
        std::cout << "GetNumberOfMaterials " << std::endl;
        return 2;
    }

    virtual G4Material *GetMaterial(G4int idx) const {
        std::cout << "GetMaterial " << idx << std::endl;
        return nullptr;
    }

    virtual void ComputeTransformation(const G4int no,
                                       G4VPhysicalVolume *currentPV) const {
        std::cout << "ComputeTransformation " << no << std::endl;
        std::cout << currentPV << std::endl;
    }

};

#endif // GamImageNestedParameterisation_h
