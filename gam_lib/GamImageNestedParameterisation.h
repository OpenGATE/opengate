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
#include "G4VTouchable.hh"
#include "itkImage.h"

class GamImageNestedParameterisation : public G4VNestedParameterisation {

public:

    std::vector<G4double> fpZ;
    std::vector<G4Material *> fMaterials;
    typedef itk::Image<float, 3> ImageType;
    ImageType::Pointer cpp_image;

    GamImageNestedParameterisation() : G4VNestedParameterisation() {
        // Create the image pointer
        // size and allocation will be performed on the py side
        cpp_image = ImageType::New();
    }

    void initialize_image() {
        // the following must be int, not auto (will be negative)
        int size_z = cpp_image->GetLargestPossibleRegion().GetSize()[2];
        auto spacing_z = cpp_image->GetSpacing()[2];
        std::cout << "init image " << size_z << " " << spacing_z << std::endl;
        double hs = spacing_z / 2.0; // half pixel along Z dimension
        for (int iz = 0; iz < size_z; iz++) {
            auto zp = (-size_z + 1 + 2 * iz) * hs;
            fpZ.push_back(zp * CLHEP::mm);
            std::cout << "iz " << iz << " " << zp * CLHEP::mm << std::endl;
        }
        std::cout << "img " << cpp_image->GetLargestPossibleRegion().GetSize() << std::endl;
        std::cout << "img " << cpp_image->GetSpacing() << std::endl;
    }

    void initialize_material(std::vector<std::string> materials) {
        fMaterials.resize(0);
        for (auto s:materials) {
            std::cout << "mat " << s << " " << std::endl;
            //auto m = G4NistManager::Instance()->FindOrBuildMaterial(s);
            auto m = G4Material::GetMaterial(s);
            if (m == nullptr) {
                std::cout << "Cannot find the material " << s << std::endl;
                exit(0);
            }
            fMaterials.push_back(m);
        }
    }

    virtual G4Material *ComputeMaterial(G4VPhysicalVolume * /*currentVol*/,
                                        const G4int repNo,
                                        const G4VTouchable *parentTouch = nullptr) {
        //std::cout << "I am in ComputeMaterial " << std::endl;
        //std::cout << currentVol << std::endl;
        //std::cout << repNo << std::endl;
        //std::cout << parentTouch << std::endl;

        if (parentTouch == nullptr) {
            std::cout << "Compute Material without parentTouch " << repNo << std::endl;
            return G4NistManager::Instance()->FindOrBuildMaterial("G4_AIR");
            // FIXME AIR ?? really ?
        }

        G4int ix = parentTouch->GetReplicaNumber(0);
        G4int iy = parentTouch->GetReplicaNumber(1);
        G4int iz = repNo;
        //std::cout << "Index " << ix << " " << iy << " " << iz << std::endl;

        ImageType::IndexType index;
        index[0] = ix;
        index[1] = iy;
        index[2] = iz;
        if (cpp_image->GetLargestPossibleRegion().IsInside(index)) {
            int i = int(cpp_image->GetPixel(index));
            //std::cout << "i = " << i << std::endl;
            auto mat = fMaterials[i];
            //std::cout << "m " << i << " " << mat->GetName() << " " << mat->GetDensity() << std::endl;
            return mat;
        } else {
            //std::cout << "outside " << index << std::endl;
            auto m = G4NistManager::Instance()->FindOrBuildMaterial("G4_AIR");
            return m;
        }

        //auto water = G4NistManager::Instance()->FindOrBuildMaterial("G4_WATER");
        //return water;
    }

    virtual G4int GetNumberOfMaterials() const {
        std::cout << "GetNumberOfMaterials " << fMaterials.size() << std::endl;
        return fMaterials.size();
    }

    virtual G4Material *GetMaterial(G4int idx) const {
        std::cout << "GetMaterial " << idx << " " << fMaterials[idx]->GetName() << std::endl;
        //auto water = G4NistManager::Instance()->FindOrBuildMaterial("G4_WATER");
        //return water;
        return fMaterials[idx];
    }

    virtual void ComputeTransformation(const G4int no,
                                       G4VPhysicalVolume *currentPV) const {
        G4ThreeVector t(0., 0., fpZ[no]);
        currentPV->SetTranslation(t);
    }

};

#endif // GamImageNestedParameterisation_h
