/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   ------------------------------------ -------------- */

#ifndef GATE_MATERIAL_MU_HANDLER_HH
#define GATE_MATERIAL_MU_HANDLER_HH

#include "G4LossTableManager.hh"
#include "G4MaterialCutsCouple.hh"
#include "G4ParticleTable.hh"
#include "G4UnitsTable.hh"

#include "GateMuTables.h"
#include <map>
#include <memory>
#include <tuple>

struct MuStorageStruct {
  double energy;
  int isAtomicShell;
  double atomicShellEnergy;
  double mu;
  double muen;

  MuStorageStruct(double e, int i, double a) {
    energy = e;
    isAtomicShell = i;
    atomicShellEnergy = a;
    mu = 0.;
    muen = 0.;
  }

  bool operator<(const MuStorageStruct &str) const {
    return (energy < str.energy);
  }
};

class GateMaterialMuHandler {

public:
  static std::shared_ptr<GateMaterialMuHandler>
  GetInstance(std::string database, double energy_max);

  ~GateMaterialMuHandler();

  double GetDensity(const G4MaterialCutsCouple *);

  double GetMuEnOverRho(const G4MaterialCutsCouple *, double);

  double GetMuEn(const G4MaterialCutsCouple *, double);

  double GetMuOverRho(const G4MaterialCutsCouple *, double);

  double GetMu(const G4MaterialCutsCouple *, double);

  [[nodiscard]] G4String GetDatabaseName() const;

  GateMuTable *GetMuTable(const G4MaterialCutsCouple *);

  void SetDatabaseName(G4String name);

  void SetEMin(double e);

  void SetEMax(double e);

  void SetENumber(int n);

  void SetAtomicShellEMin(double e);

  void SetPrecision(double p);

  GateMaterialMuHandler();

  // Initialization
  void Initialize();

  // Precalculated coefficients (by element)
  void InitElementTable();

  void ConstructMaterial(const G4MaterialCutsCouple *);

  // Complete simulation of coefficients
  void SimulateMaterialTable();

  void ConstructEnergyList(std::vector<MuStorageStruct> *, const G4Material *);

  static void MergeAtomicShell(std::vector<MuStorageStruct> *);

  static double ProcessOneShot(G4VEmModel *, std::vector<G4DynamicParticle *> *,
                               const G4MaterialCutsCouple *,
                               const G4DynamicParticle *);

  static double SquaredSigmaOnMean(double, double, double);

  void CheckLastCall(const G4MaterialCutsCouple *);

  // static GateMaterialMuHandler *fSingletonMaterialMuHandler;
  static std::map<std::tuple<std::string, double>,
                  std::shared_ptr<GateMaterialMuHandler>>
      fInstances;

  std::map<const G4MaterialCutsCouple *, GateMuTable *> fCoupleTable;
  GateMuTable **fElementsTable;
  int fElementNumber;
  G4String fDatabaseName;
  bool fIsInitialized;
  double fEnergyMin;
  double fEnergyMax;
  int fEnergyNumber;
  double fAtomicShellEnergyMin;
  double fPrecision;
  const G4MaterialCutsCouple *fLastCouple;
  GateMuTable *fLastMuTable;
};

#endif
