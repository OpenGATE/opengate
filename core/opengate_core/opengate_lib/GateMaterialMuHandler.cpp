/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   ------------------------------------ -------------- */

#include "GateMaterialMuHandler.h"
#include "GateHelpers.h"
#include "GateMuDatabase.h"
#include "GateMuTables.h"

#include "G4Gamma.hh"
#include "G4ProcessManager.hh"
#include "G4ProcessVector.hh"
#include "G4ProductionCutsTable.hh"
#include "G4VAtomDeexcitation.hh"
#include "G4VEmProcess.hh"

GateMaterialMuHandler *GateMaterialMuHandler::fSingletonMaterialMuHandler =
    nullptr;

GateMaterialMuHandler::GateMaterialMuHandler() {
  fIsInitialized = false;
  fElementNumber = -1;
  fElementsTable = nullptr;
  fDatabaseName = "EPDL";
  fEnergyMin = 250. * CLHEP::eV;
  fEnergyMax = 1. * CLHEP::MeV;
  fEnergyNumber = 40;
  fAtomicShellEnergyMin = 1. * CLHEP::keV;
  fPrecision = 0.01;
  fLastCouple = nullptr;
  fLastMuTable = nullptr;
}

GateMaterialMuHandler::~GateMaterialMuHandler() { delete[] fElementsTable; }

void GateMaterialMuHandler::CheckLastCall(const G4MaterialCutsCouple *couple) {
  if (!fIsInitialized) {
    Initialize();
  }

  if (couple != fLastCouple) {
    fLastCouple = couple;
    fLastMuTable = fCoupleTable[fLastCouple];
  }
}

double GateMaterialMuHandler::GetDensity(const G4MaterialCutsCouple *couple) {
  CheckLastCall(couple);
  return fLastMuTable->GetDensity();
}

double GateMaterialMuHandler::GetMuEnOverRho(const G4MaterialCutsCouple *couple,
                                             double energy) {
  CheckLastCall(couple);
  return fLastMuTable->GetMuEnOverRho(energy);
}

double GateMaterialMuHandler::GetMuEn(const G4MaterialCutsCouple *couple,
                                      double energy) {
  CheckLastCall(couple);
  return fLastMuTable->GetMuEn(energy);
}

double GateMaterialMuHandler::GetMuOverRho(const G4MaterialCutsCouple *couple,
                                           double energy) {
  CheckLastCall(couple);
  return fLastMuTable->GetMuOverRho(energy);
}

double GateMaterialMuHandler::GetMu(const G4MaterialCutsCouple *couple,
                                    double energy) {
  CheckLastCall(couple);
  return fLastMuTable->GetMu(energy);
}

GateMuTable *
GateMaterialMuHandler::GetMuTable(const G4MaterialCutsCouple *couple) {
  CheckLastCall(couple);
  return fLastMuTable;
}

inline double interpolation(double Xa, double Xb, double Ya, double Yb,
                            double x) {
  return exp(log(Ya) + log(Yb / Ya) / log(Xb / Xa) * log(x / Xa));
}

void GateMaterialMuHandler::Initialize() {
  if (fDatabaseName == "simulated") {
    SimulateMaterialTable();
  } else if (fDatabaseName == "NIST" || fDatabaseName == "EPDL") {
    InitElementTable();

    G4ProductionCutsTable *productionCutList =
        G4ProductionCutsTable::GetProductionCutsTable();
    std::map<const G4MaterialCutsCouple *, GateMuTable *>::iterator it;

    for (G4int m = 0; m < productionCutList->GetTableSize(); m++) {
      const G4MaterialCutsCouple *couple =
          productionCutList->GetMaterialCutsCouple(m);
      it = fCoupleTable.find(couple);
      if (it == fCoupleTable.end()) {
        const G4Material *material = couple->GetMaterial();
        bool materialNotExist = true;
        auto it2 = fCoupleTable.begin();

        while (it2 != fCoupleTable.end()) {
          if (it2->first->GetMaterial() == material) {
            fCoupleTable.insert(
                std::pair<const G4MaterialCutsCouple *, GateMuTable *>(
                    couple, it2->second));
            materialNotExist = false;
            break;
          }
          it2++;
        }

        if (materialNotExist) {
          ConstructMaterial(couple);
        }
      }
    }
  } else {
    std::ostringstream oss;
    oss << "GateMaterialMuHandler -- mu/mu_en database option '"
        << fDatabaseName
        << "' doesn't exist. Available database are 'NIST', 'EPDL' and 'user'"
        << std::endl;
    Fatal(oss.str());
  }

  fIsInitialized = true;
}

void GateMaterialMuHandler::ConstructMaterial(
    const G4MaterialCutsCouple *couple) {
  const G4Material *material = couple->GetMaterial();

  int nb_e = 0;
  auto nb_of_elements = material->GetNumberOfElements();
  for (int i = 0; i < nb_of_elements; i++)
    nb_e += fElementsTable[(int)material->GetElement(i)->GetZ()]->GetSize();

  auto *energies = new double[nb_e];
  int *index = new int[nb_of_elements];
  auto **e_tables = new double *[nb_of_elements];
  auto **mu_tables = new double *[nb_of_elements];
  auto **mu_en_tables = new double *[nb_of_elements];

  const G4double *FractionMass = material->GetFractionVector();

  for (int i = 0; i < nb_of_elements; i++) {
    e_tables[i] =
        fElementsTable[(int)material->GetElement(i)->GetZ()]->GetEnergies();
    mu_tables[i] =
        fElementsTable[(int)material->GetElement(i)->GetZ()]->GetMuTable();
    mu_en_tables[i] =
        fElementsTable[(int)material->GetElement(i)->GetZ()]->GetMuEnTable();
    index[i] = 0;
  }
  for (int i = 0; i < nb_e; i++) {
    int min_table = 0;
    while (
        index[min_table] >=
        fElementsTable[(int)material->GetElement(min_table)->GetZ()]->GetSize())
      min_table++;
    for (int j = min_table + 1; j < nb_of_elements; j++)
      if (e_tables[j][index[j]] < e_tables[min_table][index[min_table]])
        min_table = j;
    energies[i] = e_tables[min_table][index[min_table]];

    if (i > 0) {
      if (energies[i] == energies[i - 1]) {
        if (index[min_table] > 0 &&
            e_tables[min_table][index[min_table]] ==
                e_tables[min_table][index[min_table] - 1])
          ;
        else {
          i--;
          nb_e--;
        }
      }
    }
    index[min_table]++;
  }

  // And now computing mu_en
  auto *MuEn = new double[nb_e];
  auto *Mu = new double[nb_e];
  for (int i = 0; i < nb_of_elements; i++) {
    index[i] = 0;
  }

  // Assume that all table begin with the same energy
  for (int i = 0; i < nb_e; i++) {
    MuEn[i] = 0.0;
    Mu[i] = 0.0;
    double current_e = energies[i];
    for (int j = 0; j < nb_of_elements; j++) {
      // You never need to advance twice
      if (e_tables[j][index[j]] < current_e)
        index[j]++;
      if (e_tables[j][index[j]] == current_e) {
        Mu[i] += FractionMass[j] * mu_tables[j][index[j]];
        MuEn[i] += FractionMass[j] * mu_en_tables[j][index[j]];
        if (i != nb_e - 1)
          if (e_tables[j][index[j]] == e_tables[j][index[j] + 1])
            index[j]++;
      } else {
        Mu[i] += FractionMass[j] *
                 interpolation(e_tables[j][index[j] - 1], e_tables[j][index[j]],
                               mu_tables[j][index[j] - 1],
                               mu_tables[j][index[j]], current_e);
        MuEn[i] +=
            FractionMass[j] *
            interpolation(e_tables[j][index[j] - 1], e_tables[j][index[j]],
                          mu_en_tables[j][index[j] - 1],
                          mu_en_tables[j][index[j]], current_e);
      }
    }
  }

  auto *table = new GateMuTable(couple, nb_e);

  for (int i = 0; i < nb_e; i++) {
    table->PutValue(i, log(energies[i]), log(Mu[i]), log(MuEn[i]));
  }

  fCoupleTable.insert(
      std::pair<const G4MaterialCutsCouple *, GateMuTable *>(couple, table));

  delete[] energies;
  delete[] index;
  delete[] e_tables;
  delete[] mu_tables;
  delete[] mu_en_tables;
  delete[] MuEn;
  delete[] Mu;
}

void GateMaterialMuHandler::InitElementTable() {
  const int *energyNumberList;
  const float *data;

  if (fDatabaseName == "NIST") {
    fElementNumber = NIST_mu_muen_data_elementNumber;
    energyNumberList = NIST_mu_muen_data_energyNumber;
    data = NIST_mu_muen_data;
  } else if (fDatabaseName == "EPDL") {
    fElementNumber = EPDL_mu_muen_data_elementNumber;
    energyNumberList = EPDL_mu_muen_data_energyNumber;
    data = EPDL_mu_muen_data;
  }

  fElementsTable = new GateMuTable *[fElementNumber + 1];
  int index = 0;

  for (int i = 0; i < fElementNumber + 1; i++) {
    auto energyNumber = energyNumberList[i];
    auto *table = new GateMuTable(nullptr, energyNumber);
    fElementsTable[i] = table;

    for (int j = 0; j < energyNumber; j++) {
      table->PutValue(j, data[index], data[index + 1], data[index + 2]);
      index += 3;
    }
  }
}

void GateMaterialMuHandler::SimulateMaterialTable() {
  // Get process list for gamma
  G4ProcessVector *processListForGamma =
      G4Gamma::Gamma()->GetProcessManager()->GetProcessList();
  G4ParticleDefinition *gamma = G4Gamma::Gamma();
  // Check if fluo is active
  bool isFluoActive = false;
  if (G4LossTableManager::Instance()->AtomDeexcitation()) {
    isFluoActive =
        G4LossTableManager::Instance()->AtomDeexcitation()->IsFluoActive();
  }

  // Find photoelectric (PE), compton scattering (CS) (+ particleChange) and
  // rayleigh scattering (RS) models
  G4VEmModel *modelPE = nullptr;
  G4VEmModel *modelCS = nullptr;
  G4VEmModel *modelRS = nullptr;
  G4ParticleChangeForGamma *particleChangeCS = nullptr;

  // Useful members for the loops
  // cuts and materials
  G4ProductionCutsTable *productionCutList =
      G4ProductionCutsTable::GetProductionCutsTable();
  G4String materialName;

  // particles
  G4DynamicParticle primary(gamma, G4ThreeVector(1., 0., 0.));
  std::vector<G4DynamicParticle *> secondaries;
  double incidentEnergy;

  // (mu ; mu_en) calculations
  std::map<const G4MaterialCutsCouple *, GateMuTable *>::iterator it;
  double totalFluoPE;
  double totalFluoCS;
  double totalScatterCS;
  double crossSectionPE;
  double crossSectionCS;
  double crossSectionRS;
  double fPE;
  double fCS;
  double mu(0.);
  double muen(0.);

  // mu_en uncertainty
  double squaredFluoPE; // sum of squared PE fluorescence energy measurement
  double squaredFluoCS; // sum of squared CS fluorescence energy measurement
  double
      squaredScatterCS; // sum of squared CS scattered photon energy measurement
  int shotNumberPE;
  int shotNumberCS;
  double squaredSigmaPE; // squared PE uncertainty weighted by corresponding
                         // squared cross-section
  double squaredSigmaCS; // squared CS uncertainty weighted by corresponding
                         // squared cross-section
  double squaredSigmaMuEn(0.); // squared mu_en uncertainty

  // - loops options
  std::vector<MuStorageStruct> muStorage;

  // Loop on material
  for (G4int m = 0; m < productionCutList->GetTableSize(); m++) {
    const G4MaterialCutsCouple *couple =
        productionCutList->GetMaterialCutsCouple(m);
    const G4Material *material = couple->GetMaterial();
    // materialName = material->GetName();
    it = fCoupleTable.find(couple);
    if (it == fCoupleTable.end()) {
      double energyCutForGamma = productionCutList->ConvertRangeToEnergy(
          gamma, material,
          couple->GetProductionCuts()->GetProductionCut("gamma"));
      // Construct energy list (energy, atomicShellEnergy)
      ConstructEnergyList(&muStorage, material);

      // Loop on energy
      for (auto &e : muStorage) {
        incidentEnergy = e.energy;
        primary.SetKineticEnergy(incidentEnergy);

        // find the physical models according to the gamma energy
        for (G4int i = 0; i < processListForGamma->size(); i++) {
          size_t physicRegionNumber = 0;
          G4String processName = (*processListForGamma)[i]->GetProcessName();
          if (processName == "PhotoElectric" || processName == "phot") {
            modelPE = (dynamic_cast<G4VEmProcess *>((*processListForGamma)[i]))
                          ->SelectModelForMaterial(incidentEnergy,
                                                   physicRegionNumber);
          } else if (processName == "Compton" || processName == "compt") {
            auto *processCS =
                dynamic_cast<G4VEmProcess *>((*processListForGamma)[i]);
            modelCS = processCS->SelectModelForMaterial(incidentEnergy,
                                                        physicRegionNumber);

            // Get the G4VParticleChange of compton scattering by running a
            // fictive step (no simple 'get' function available)
            G4Track myTrack(
                new G4DynamicParticle(gamma, G4ThreeVector(1., 0., 0.), 0.01),
                0., G4ThreeVector(0., 0., 0.));
            myTrack.SetTrackStatus(
                fStopButAlive); // to get a fast return (see
                                // G4VEmProcess::PostStepDoIt(...))
            G4Step myStep;
            particleChangeCS = dynamic_cast<G4ParticleChangeForGamma *>(
                processCS->PostStepDoIt((const G4Track)(myTrack), myStep));
          } else if (processName == "RayleighScattering" ||
                     processName == "Rayl") {
            modelRS = (dynamic_cast<G4VEmProcess *>((*processListForGamma)[i]))
                          ->SelectModelForMaterial(incidentEnergy,
                                                   physicRegionNumber);
          }
        }

        // Cross-section calculation
        double density = material->GetDensity() / (CLHEP::g / CLHEP::cm3);
        crossSectionPE = 0.;
        crossSectionCS = 0.;
        crossSectionRS = 0.;
        if (modelPE) {
          crossSectionPE =
              modelPE->CrossSectionPerVolume(material, gamma, incidentEnergy,
                                             energyCutForGamma, 10.) *
              CLHEP::cm / density;
        }
        if (modelCS) {
          crossSectionCS =
              modelCS->CrossSectionPerVolume(material, gamma, incidentEnergy,
                                             energyCutForGamma, 10.) *
              CLHEP::cm / density;
        }
        if (modelRS) {
          crossSectionRS =
              modelRS->CrossSectionPerVolume(material, gamma, incidentEnergy,
                                             energyCutForGamma, 10.) *
              CLHEP::cm / density;
        }

        // mu_en and uncertainty calculation
        squaredFluoPE = 0.;
        squaredFluoCS = 0.;
        squaredScatterCS = 0.;
        totalFluoPE = 0.;
        totalFluoCS = 0.;
        totalScatterCS = 0.;
        shotNumberPE = 0;
        shotNumberCS = 0;
        squaredSigmaPE = 0.;
        squaredSigmaCS = 0.;
        fPE = 1.;
        fCS = 1.;
        double trialFluoEnergy;
        double precision = 10e6;
        int initialShotNumber = 100;
        int initialShotNumberPE = int(initialShotNumber / 2);

        int variableShotNumberPE = 0;
        if (modelPE && isFluoActive) {
          variableShotNumberPE = initialShotNumberPE;
        }

        int variableShotNumberCS = 0;
        if (modelCS) {
          variableShotNumberCS = initialShotNumber - variableShotNumberPE;
        }

        // Loop on shot
        while (precision > fPrecision) {
          // photoElectric shots to get the mean fluorescence photon energy
          for (int iPE = 0; iPE < variableShotNumberPE; iPE++) {
            trialFluoEnergy =
                ProcessOneShot(modelPE, &secondaries, couple, &primary);
            shotNumberPE++;

            totalFluoPE += trialFluoEnergy;
            squaredFluoPE += (trialFluoEnergy * trialFluoEnergy);
          }

          // compton shots to get the mean fluorescence and scatter photon
          // energy
          for (int iCS = 0; iCS < variableShotNumberCS; iCS++) {
            trialFluoEnergy =
                ProcessOneShot(modelCS, &secondaries, couple, &primary);
            shotNumberCS++;

            totalFluoCS += trialFluoEnergy;
            squaredFluoCS += (trialFluoEnergy * trialFluoEnergy);
            auto trialScatterEnergy =
                particleChangeCS->GetProposedKineticEnergy();
            totalScatterCS += trialScatterEnergy;
            squaredScatterCS += (trialScatterEnergy * trialScatterEnergy);
          }

          // average fractions of the incident energy E that is transferred to
          // kinetic energy of charged particles (for muen)
          if (shotNumberPE) {
            fPE = 1. - ((totalFluoPE / double(shotNumberPE)) / incidentEnergy);
            squaredSigmaPE =
                SquaredSigmaOnMean(squaredFluoPE, totalFluoPE, shotNumberPE) *
                crossSectionPE * crossSectionPE;
          }
          if (shotNumberCS) {
            fCS =
                1. - (((totalScatterCS + totalFluoCS) / double(shotNumberCS)) /
                      incidentEnergy);
            squaredSigmaCS =
                (SquaredSigmaOnMean(squaredFluoCS, totalFluoCS, shotNumberCS) +
                 SquaredSigmaOnMean(squaredScatterCS, totalScatterCS,
                                    shotNumberCS)) *
                crossSectionCS * crossSectionCS;
          }

          // mu/rho and mu_en/rho calculation
          muen = fPE * crossSectionPE + fCS * crossSectionCS;

          // uncertainty calculation
          squaredSigmaMuEn = (squaredSigmaPE + squaredSigmaCS) /
                             (incidentEnergy * incidentEnergy);
          precision = sqrt(squaredSigmaMuEn) / muen;

          if (modelPE && isFluoActive) {
            if (squaredSigmaPE > 0) {
              variableShotNumberPE =
                  (int)floor(0.5 + double(initialShotNumber) *
                                       sqrt(squaredSigmaPE /
                                            (squaredSigmaPE + squaredSigmaCS)));
            } else {
              variableShotNumberPE = initialShotNumberPE;
            }
          }
          if (modelCS) {
            variableShotNumberCS = initialShotNumber - variableShotNumberPE;
          }
        }

        mu = crossSectionPE + crossSectionCS + crossSectionRS;
        e.mu = mu;
        e.muen = muen;
      }

      // Interpolation of mu,mu_en for energy bordering an atomic transition
      // (see ConstructEnergyList(...))
      MergeAtomicShell(&muStorage);

      // Fill mu,mu_en table for this material
      auto *table = new GateMuTable(couple, muStorage.size());

      for (G4int e = 0; e < muStorage.size(); e++) {
        table->PutValue(e, log(muStorage[e].energy), log(muStorage[e].mu),
                        log(muStorage[e].muen));
      }
      fCoupleTable.insert(
          std::pair<const G4MaterialCutsCouple *, GateMuTable *>(couple,
                                                                 table));
    }
  }
}

double GateMaterialMuHandler::ProcessOneShot(
    G4VEmModel *model, std::vector<G4DynamicParticle *> *secondaries,
    const G4MaterialCutsCouple *couple, const G4DynamicParticle *primary) {
  secondaries->clear();
  model->SampleSecondaries(secondaries, couple, primary, 0., 0.);
  double energy = 0.;
  for (auto &secondary : *secondaries) {
    if (secondary->GetParticleDefinition()->GetParticleName() == "gamma") {
      energy += secondary->GetKineticEnergy();
    }
    delete secondary;
  }

  return energy;
}

double GateMaterialMuHandler::SquaredSigmaOnMean(double sumOfSquaredMeasurement,
                                                 double sumOfMeasurement,
                                                 double numberOfMeasurement) {
  sumOfMeasurement = sumOfMeasurement / numberOfMeasurement;
  return ((sumOfSquaredMeasurement / numberOfMeasurement) -
          (sumOfMeasurement * sumOfMeasurement)) /
         numberOfMeasurement;
}

void GateMaterialMuHandler::ConstructEnergyList(
    std::vector<MuStorageStruct> *muStorage, const G4Material *material) {
  muStorage->clear();
  double energyStep =
      exp((log(fEnergyMax) - log(fEnergyMin)) / double(fEnergyNumber));
  double deltaEnergy = 50.0 * CLHEP::eV;

  // - basic list
  muStorage->emplace_back(fEnergyMin, 0, 0.);
  for (int e = 0; e < fEnergyNumber; e++) {
    muStorage->emplace_back((*muStorage)[e].energy * energyStep, 0, 0.);
  }

  // - add atomic shell energies
  auto elementNumber = material->GetNumberOfElements();
  for (int i = 0; i < elementNumber; i++) {
    const G4Element *element = material->GetElement(i);
    for (int j = 0; j < material->GetElement(i)->GetNbOfAtomicShells(); j++) {
      double atomicShellEnergy = element->GetAtomicShell(j);
      if (atomicShellEnergy > fAtomicShellEnergyMin &&
          atomicShellEnergy > fEnergyMin) {
        double infEnergy = atomicShellEnergy - deltaEnergy;
        double supEnergy = atomicShellEnergy + deltaEnergy;
        unsigned int elementToErase = -1;
        for (unsigned int e = 0; e < muStorage->size(); e++) {
          if (((*muStorage)[e].energy > infEnergy) &&
              ((*muStorage)[e].energy < supEnergy)) {
            elementToErase = e;
            break;
          }
        }
        if (elementToErase + 1) {
          muStorage->erase(muStorage->begin() + elementToErase);
        }

        muStorage->emplace_back(atomicShellEnergy - deltaEnergy, -1,
                                atomicShellEnergy); // inf
        muStorage->emplace_back(atomicShellEnergy + deltaEnergy, +1,
                                atomicShellEnergy); // sup
      }
    }
  }
  std::sort(muStorage->begin(), muStorage->end());
}

void GateMaterialMuHandler::MergeAtomicShell(
    std::vector<MuStorageStruct> *muStorage) {
  for (G4int e = 0; e < muStorage->size(); e++) {
    int isAtomicShell = (*muStorage)[e].isAtomicShell;
    if (isAtomicShell != 0) {
      auto neighbourIndex = e + isAtomicShell;
      if ((neighbourIndex > -1) && (neighbourIndex < (int)muStorage->size())) {
        double mu = interpolation(
            (*muStorage)[neighbourIndex].energy, (*muStorage)[e].energy,
            (*muStorage)[neighbourIndex].mu, (*muStorage)[e].mu,
            (*muStorage)[e].atomicShellEnergy);

        double muen = interpolation(
            (*muStorage)[neighbourIndex].energy, (*muStorage)[e].energy,
            (*muStorage)[neighbourIndex].muen, (*muStorage)[e].muen,
            (*muStorage)[e].atomicShellEnergy);

        (*muStorage)[e].mu = mu;
        (*muStorage)[e].muen = muen;
      }
      (*muStorage)[e].energy = (*muStorage)[e].atomicShellEnergy;
    }
  }
}

GateMaterialMuHandler *GateMaterialMuHandler::GetInstance() {
  if (fSingletonMaterialMuHandler == nullptr) {
    fSingletonMaterialMuHandler = new GateMaterialMuHandler();
  }
  return fSingletonMaterialMuHandler;
}

G4String GateMaterialMuHandler::GetDatabaseName() const {
  return fDatabaseName;
}

void GateMaterialMuHandler::SetDatabaseName(G4String name) {
  fDatabaseName = std::move(name);
}

void GateMaterialMuHandler::SetEMin(double e) { fEnergyMin = e; }

void GateMaterialMuHandler::SetEMax(double e) { fEnergyMax = e; }

void GateMaterialMuHandler::SetENumber(int n) { fEnergyNumber = n; }

void GateMaterialMuHandler::SetAtomicShellEMin(double e) {
  fAtomicShellEnergyMin = e;
}

void GateMaterialMuHandler::SetPrecision(double p) { fPrecision = p; }
