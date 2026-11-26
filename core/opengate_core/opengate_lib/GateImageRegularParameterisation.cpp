/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#include "GateImageRegularParameterisation.h"
#include "GateHelpers.h"
#include <G4Box.hh>
#include <G4Material.hh>
#include <G4PVParameterised.hh>
#include <G4ParticleTable.hh>
#include <G4ProcessManager.hh>
#include <G4ScoreSplittingProcess.hh>

bool GateImageRegularParameterisation::fRegularNavigationIsUsed = false;

void GateImageRegularParameterisation::DeactivateScoreSplitting() {
  auto *it = G4ParticleTable::GetParticleTable()->GetIterator();
  it->reset();
  while ((*it)()) {
    auto *pm = it->value()->GetProcessManager();
    if (pm == nullptr)
      continue;
    auto *pv = pm->GetProcessList();
    for (std::size_t i = 0; i < pv->size(); i++) {
      auto *p = (*pv)[i];
      if (dynamic_cast<G4ScoreSplittingProcess *>(p) != nullptr &&
          pm->GetProcessActivation(p)) {
        pm->SetProcessActivation(p, false);
      }
    }
  }
}

GateImageRegularParameterisation::GateImageRegularParameterisation()
    : G4PhantomParameterisation() {
  cpp_image = ImageType::New();
}

void GateImageRegularParameterisation::initialize_image() {
  // the copy number of a voxel is ix + nx * (iy + ny * iz) (as in
  // G4PhantomParameterisation), the same order as the itk buffer
  const auto size = cpp_image->GetLargestPossibleRegion().GetSize();
  const auto spacing = cpp_image->GetSpacing();
  SetVoxelDimensions(spacing[0] / 2.0 * CLHEP::mm, spacing[1] / 2.0 * CLHEP::mm,
                     spacing[2] / 2.0 * CLHEP::mm);
  SetNoVoxels(size[0], size[1], size[2]);
  const std::size_t n = size[0] * size[1] * size[2];
  fLabels.resize(n);
  const auto *buffer = cpp_image->GetBufferPointer();
  for (std::size_t i = 0; i < n; i++)
    fLabels[i] = buffer[i];
  SetMaterialIndices(fLabels.data());
}

void GateImageRegularParameterisation::initialize_material(
    std::vector<std::string> materials) {
  fImageMaterials.resize(0);
  for (const auto &s : materials) {
    auto *m = G4Material::GetMaterial(s);
    if (m == nullptr) {
      Fatal("GateImageRegularParameterisation: cannot find the material " + s);
    }
    fImageMaterials.push_back(m);
  }
  SetMaterials(fImageMaterials);
}

void GateImageRegularParameterisation::Construct(
    const std::string &name, G4LogicalVolume *containerLV,
    G4VPhysicalVolume *containerPV, const bool skipEqualMaterials) {
  for (auto l : fLabels) {
    if (l >= fImageMaterials.size())
      Fatal("GateImageRegularParameterisation: a label is larger than the "
            "number of materials, for the image " +
            name);
  }
  auto *voxel = new G4Box(name + "_voxel", GetVoxelHalfX(), GetVoxelHalfY(),
                          GetVoxelHalfZ());
  fVoxelLV =
      new G4LogicalVolume(voxel, fImageMaterials[0], name + "_log_voxel");
  // the container (the image volume) must be a box filled by the voxels
  const auto *box = dynamic_cast<const G4Box *>(containerLV->GetSolid());
  if (box == nullptr)
    Fatal("GateImageRegularParameterisation: the container of " + name +
          " is not a box");
  BuildContainerSolid(containerPV);
  CheckVoxelsFillContainer(box->GetXHalfLength(), box->GetYHalfLength(),
                           box->GetZHalfLength());
  fVoxelPV =
      new G4PVParameterised(name + "_voxels", fVoxelLV, containerLV, kUndefined,
                            (G4int)GetNoVoxels(), this, false);
  fVoxelPV->SetRegularStructureId(1);
  fRegularNavigationIsUsed = true;
  SetSkipEqualMaterials(skipEqualMaterials);
}
