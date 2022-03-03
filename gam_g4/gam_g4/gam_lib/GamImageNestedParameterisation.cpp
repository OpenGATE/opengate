/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#include "GamImageNestedParameterisation.h"

GamImageNestedParameterisation::GamImageNestedParameterisation() : G4VNestedParameterisation() {
    // Create the image pointer
    // size and allocation will be performed on the py side
    cpp_image = ImageType::New();
}

void GamImageNestedParameterisation::initialize_image() {
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

void GamImageNestedParameterisation::initialize_material(std::vector<std::string> materials) {
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

G4Material *GamImageNestedParameterisation::ComputeMaterial(G4VPhysicalVolume * /*currentVol*/,
                                                            const G4int repNo,
                                                            const G4VTouchable *parentTouch) {
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

G4int GamImageNestedParameterisation::GetNumberOfMaterials() const {
    return fMaterials.size();
}

G4Material *GamImageNestedParameterisation::GetMaterial(G4int idx) const {
    return fMaterials[idx];
}

void GamImageNestedParameterisation::ComputeTransformation(const G4int no,
                                                           G4VPhysicalVolume *currentPV) const {
    G4ThreeVector t(0., 0., fpZ[no]);
    currentPV->SetTranslation(t);
}
