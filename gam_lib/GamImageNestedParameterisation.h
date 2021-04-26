/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#ifndef GamImageNestedParameterisation_h
#define GamImageNestedParameterisation_h

#include "GamHelpers.h"
#include "G4VNestedParameterisation.hh"
#include "G4NistManager.hh"
#include "G4VPhysicalVolume.hh"
#include "G4VTouchable.hh"
#include "itkImage.h"

class GamImageNestedParameterisation : public G4VNestedParameterisation {

public:

    // Slice position in mm
    std::vector<G4double> fpZ;
    // List of pixel value <-> material
    std::vector<G4Material *> fMaterials;
    // The image, float for the moment. Short later.
    typedef itk::Image<float, 3> ImageType;
    ImageType::Pointer cpp_image;

    GamImageNestedParameterisation() : G4VNestedParameterisation() {
        // Create the image pointer
        // size and allocation will be performed on the py side
        cpp_image = ImageType::New();
    }

    void initialize_image() {
        // the following must be int, not auto (will be negative)
        fpZ.clear();
        int size_z = cpp_image->GetLargestPossibleRegion().GetSize()[2];
        auto spacing_z = cpp_image->GetSpacing()[2];
        double hs = spacing_z / 2.0; // half pixel along Z dimension
        double offset = -size_z / 2.0 * spacing_z + hs;
        for (int iz = 0; iz < size_z; iz++) {
            //auto zp = (-size_z + 1 + 2 * iz) * hs;
            auto zp = offset + iz * spacing_z;
            fpZ.push_back(zp * CLHEP::mm);
        }
    }

    void initialize_material(std::vector<std::string> materials) {
        fMaterials.resize(0);
        for (auto s:materials) {
            auto m = G4Material::GetMaterial(s);
            if (m == nullptr) {
                std::cout << "GamImageNestedParameterisation: cannot find the material " << s << std::endl;
                exit(0);
            }
            fMaterials.push_back(m);
        }
    }

    virtual G4Material *ComputeMaterial(G4VPhysicalVolume * /*currentVol*/,
                                        const G4int repNo,
                                        const G4VTouchable *parentTouch = nullptr) {
        if (parentTouch == nullptr) {
            return G4NistManager::Instance()->FindOrBuildMaterial("G4_AIR");
            // FIXME AIR ?? really ?
        }

        // Get voxel index
        G4int ix = parentTouch->GetReplicaNumber(0);
        G4int iy = parentTouch->GetReplicaNumber(1);
        G4int iz = repNo;
        ImageType::IndexType index;
        index[0] = ix;
        index[1] = iy;
        index[2] = iz;

        // Check if inside
        if (cpp_image->GetLargestPossibleRegion().IsInside(index)) {
            int i = int(cpp_image->GetPixel(index));
            auto mat = fMaterials[i];
            return mat;
        } else {
            // Outside the image. Should almost never be here (except rounding issue)
            auto m = G4NistManager::Instance()->FindOrBuildMaterial("G4_AIR");// FIXME AIR
            return m;
        }
    }

    virtual G4int GetNumberOfMaterials() const {
        return fMaterials.size();
    }

    virtual G4Material *GetMaterial(G4int idx) const {
        return fMaterials[idx];
    }

    virtual void ComputeTransformation(const G4int no,
                                       G4VPhysicalVolume *currentPV) const {
        G4ThreeVector t(0., 0., fpZ[no]);
        currentPV->SetTranslation(t);
    }

};

#endif // GamImageNestedParameterisation_h
