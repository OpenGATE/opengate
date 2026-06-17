/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#ifndef GateChemistryWorld_h
#define GateChemistryWorld_h

#include "G4DNABoundingBox.hh"
#include "G4ThreeVector.hh"
#include "G4VChemistryWorld.hh"
#include "globals.hh"

#include <map>

class GateChemistryWorld : public G4VChemistryWorld {
public:
  GateChemistryWorld() = default;
  ~GateChemistryWorld() override = default;

  void ConstructChemistryBoundary() override;
  void ConstructChemistryComponents() override;

  void SetChemistryBoundary(const G4ThreeVector &translation,
                            const G4ThreeVector &halfSize);
  void ClearChemicalComponents();
  void AddChemicalComponent(const G4String &moleculeName,
                            G4double concentration);

  void SetPH(G4double pH) { fPH = pH; }
  G4double GetPH() const { return fPH; }

private:
  G4ThreeVector fTranslation = G4ThreeVector();
  G4ThreeVector fHalfSize = G4ThreeVector();
  std::map<G4String, G4double> fChemicalComponentDefinitions;
  G4double fPH = -1.0;
};

#endif
