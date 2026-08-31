/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#include "GateChemistryWorld.h"

#include <G4DNABoundingBox.hh>
#include <G4MolecularConfiguration.hh>
#include <G4MoleculeTable.hh>

void GateChemistryWorld::ConstructChemistryBoundary() {
  fpChemistryBoundary = std::make_unique<G4DNABoundingBox>(G4DNABoundingBox{
      fTranslation.x() + fHalfSize.x(), fTranslation.x() - fHalfSize.x(),
      fTranslation.y() + fHalfSize.y(), fTranslation.y() - fHalfSize.y(),
      fTranslation.z() + fHalfSize.z(), fTranslation.z() - fHalfSize.z()});
}

void GateChemistryWorld::ConstructChemistryComponents() {
  fpChemicalComponent.clear();
  auto *moleculeTable = G4MoleculeTable::Instance();
  for (const auto &[moleculeName, concentration] :
       fChemicalComponentDefinitions) {
    auto *configuration = moleculeTable->GetConfiguration(moleculeName, true);
    fpChemicalComponent[configuration] = concentration;
  }
}

void GateChemistryWorld::SetChemistryBoundary(const G4ThreeVector &translation,
                                              const G4ThreeVector &halfSize) {
  fTranslation = translation;
  fHalfSize = halfSize;
}

void GateChemistryWorld::ClearChemicalComponents() {
  fChemicalComponentDefinitions.clear();
  fpChemicalComponent.clear();
}

void GateChemistryWorld::AddChemicalComponent(const G4String &moleculeName,
                                              G4double concentration) {
  fChemicalComponentDefinitions[moleculeName] = concentration;
}
