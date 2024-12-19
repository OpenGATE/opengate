/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   ------------------------------------ -------------- */

#include "GateMuTables.h"

GateMuTable::GateMuTable(const G4MaterialCutsCouple *couple, G4int size) {
  fEnergy = new double[size];
  fMu = new double[size];
  fMuEn = new double[size];
  fSize = size;
  fLastMu = -1.0;
  fLastMuEn = -1.0;
  fLastEnergyMu = -1.0;
  fLastEnergyMuEn = -1.0;

  mCouple = couple;
  mDensity = -1;
  if (mCouple) {
    mMaterial = mCouple->GetMaterial();
    mDensity = mMaterial->GetDensity() / (CLHEP::g / CLHEP::cm3);
  }
}

GateMuTable::~GateMuTable() {
  delete[] fEnergy;
  delete[] fMu;
  delete[] fMuEn;
}

void GateMuTable::PutValue(int index, double energy, double mu,
                           double mu_en) const {
  fEnergy[index] = energy;
  fMu[index] = mu;
  fMuEn[index] = mu_en;
}

inline double interpol(double x1, double x, double x2, double y1, double y2) {
  return (y1 + ((y2 - y1) * (x - x1) / (x2 - x1))); // if log storage
  //   return exp( log(y1) + log(y2/y1) / log(x2/x1)* log(x/x1) ); // if no log
  //   storage
}

double GateMuTable::GetMuEnOverRho(double energy) {
  if (energy != fLastEnergyMuEn) {
    fLastEnergyMuEn = energy;

    energy = log(energy);

    int inf = 0;
    int sup = fSize - 1;
    while (sup - inf > 1) {
      int tmp_bound = (inf + sup) / 2;
      if (fEnergy[tmp_bound] > energy) {
        sup = tmp_bound;
      } else {
        inf = tmp_bound;
      }
    }
    double e_inf = fEnergy[inf];
    double e_sup = fEnergy[sup];

    if (energy > e_inf && energy < e_sup) {
      fLastMuEn = exp(interpol(e_inf, energy, e_sup, fMuEn[inf], fMuEn[sup]));
    } else {
      fLastMuEn = exp(fMuEn[inf]);
    }
  }

  return fLastMuEn;
}

double GateMuTable::GetMuEn(double energy) {
  return (GetMuEnOverRho(energy) * mDensity);
}

double GateMuTable::GetMuOverRho(double energy) {
  if (energy != fLastEnergyMu) {
    fLastEnergyMu = energy;

    energy = log(energy);

    int inf = 0;
    int sup = fSize - 1;
    while (sup - inf > 1) {
      int tmp_bound = (inf + sup) / 2;
      if (fEnergy[tmp_bound] > energy) {
        sup = tmp_bound;
      } else {
        inf = tmp_bound;
      }
    }
    double e_inf = fEnergy[inf];
    double e_sup = fEnergy[sup];

    if (energy > e_inf && energy < e_sup) {
      fLastMu = exp(interpol(e_inf, energy, e_sup, fMu[inf], fMu[sup]));
    } else {
      fLastMu = exp(fMu[inf]);
    }
  }

  return fLastMu;
}

double GateMuTable::GetMu(double energy) {
  return (GetMuOverRho(energy) * mDensity);
}

const G4MaterialCutsCouple *GateMuTable::GetMaterialCutsCouple() const {
  return mCouple;
}

const G4Material *GateMuTable::GetMaterial() const { return mMaterial; }

double GateMuTable::GetDensity() const { return mDensity; }

G4int GateMuTable::GetSize() const { return fSize; }

double *GateMuTable::GetEnergies() const { return fEnergy; }

double *GateMuTable::GetMuEnTable() const { return fMuEn; }

double *GateMuTable::GetMuTable() const { return fMu; }
