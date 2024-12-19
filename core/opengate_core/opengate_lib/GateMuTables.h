/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   ------------------------------------ -------------- */

#ifndef GATE_MU_TABLES_HH
#define GATE_MU_TABLES_HH

#include "G4Material.hh"
#include "G4MaterialCutsCouple.hh"
#include "G4UnitsTable.hh"

class GateMuTable {

public:
  GateMuTable(const G4MaterialCutsCouple *couple, G4int size);

  ~GateMuTable();

  void PutValue(int index, double energy, double mu, double mu_en) const;

  double GetMuEn(double energy);

  double GetMuEnOverRho(double energy);

  double GetMu(double energy);

  double GetMuOverRho(double energy);

  const G4MaterialCutsCouple *GetMaterialCutsCouple() const;

  const G4Material *GetMaterial() const;

  [[nodiscard]] double GetDensity() const;

  [[nodiscard]] G4int GetSize() const;

  double *GetEnergies() const;

  double *GetMuEnTable() const;

  double *GetMuTable() const;

  const G4MaterialCutsCouple *mCouple;
  const G4Material *mMaterial;
  double mDensity;
  double *fEnergy;
  double *fMu;
  double *fMuEn;
  double fLastEnergyMu;
  double fLastEnergyMuEn;
  double fLastMu;
  double fLastMuEn;
  G4int fSize;
};

#endif
