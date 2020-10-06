/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#ifndef GamImageNestedParameterisation_h
#define GamImageNestedParameterisation_h

#include "G4VNestedParameterisation.hh"
#include "G4NistManager.hh"
#include "G4VPhysicalVolume.hh"

class GamImageNestedParameterisation : public G4VNestedParameterisation {

public:

    std::vector<G4double> fpZ;

    GamImageNestedParameterisation() : G4VNestedParameterisation() {
        initialize();
    }

    void initialize() {
        int fNz = 55;
        double fdZ = 2; // half pixel ?
        double fZoffset = 0;
        for (int iz = 0; iz < fNz; iz++) {
            auto zp = (-fNz + 1 + 2 * iz) * fdZ + fZoffset;
            fpZ.push_back(zp*CLHEP::mm);
            std::cout << "slice " << iz << " " << zp << std::endl;
        }
    }

    virtual G4Material *ComputeMaterial(G4VPhysicalVolume * /*currentVol*/,
                                        const G4int /*repNo*/,
                                        const G4VTouchable *parentTouch = nullptr) {
        /*
         * std::cout << "I am in ComputeMaterial " << std::endl;
        std::cout << currentVol << std::endl;
        std::cout << repNo << std::endl;
        std::cout << parentTouch << std::endl;
         */
        auto water = G4NistManager::Instance()->FindOrBuildMaterial("G4_WATER");
        return water;
    }

    virtual G4int GetNumberOfMaterials() const {
        std::cout << "GetNumberOfMaterials " << std::endl;
        return 1;
    }

    virtual G4Material *GetMaterial(G4int idx) const {
        std::cout << "GetMaterial " << idx << std::endl;
        auto water = G4NistManager::Instance()->FindOrBuildMaterial("G4_WATER");
        return water;
    }

    virtual void ComputeTransformation(const G4int no,
                                       G4VPhysicalVolume *currentPV) const {
        G4ThreeVector t(0., 0., fpZ[no]);
        currentPV->SetTranslation(t);
        // std::cout << "ComputeTransformation " << no << " " << t << std::endl;
        //std::cout << currentPV << std::endl;
    }

};

#endif // GamImageNestedParameterisation_h
