//
// ********************************************************************
// * License and Disclaimer                                           *
// *                                                                  *
// * The  Geant4 software  is  copyright of the Copyright Holders  of *
// * the Geant4 Collaboration.  It is provided  under  the terms  and *
// * conditions of the Geant4 Software License,  included in the file *
// * LICENSE and available at  http://cern.ch/geant4/license .  These *
// * include a list of copyright holders.                             *
// *                                                                  *
// * Neither the authors of this software system, nor their employing *
// * institutes,nor the agencies providing financial support for this *
// * work  make  any representation or  warranty, express or implied, *
// * regarding  this  software system or assume any liability for its *
// * use.  Please see the license in the file  LICENSE  and URL above *
// * for the full disclaimer and the limitation of liability.         *
// *                                                                  *
// * This  code  implementation is the result of  the  scientific and *
// * technical work of the GEANT4 collaboration.                      *
// * By using,  copying,  modifying or  distributing the software (or *
// * any work based  on the software)  you  agree  to acknowledge its *
// * use  in  resulting  scientific  publications,  and indicate your *
// * acceptance of all terms of the Geant4 Software license.          *
// ********************************************************************
//
//
/// \file Hadr09.cc
/// \brief Main program of the hadronic/Hadr09 example
//
//------------------------------------------------------------------------
// This program shows how to use the class Hadronic Generator.
// The class HadronicGenerator is a kind of "hadronic generator", i.e.
// provides Geant4 final states (i.e. secondary particles) produced by
// hadron-nuclear inelastic collisions.
// Please see the class itself for more information.
//
// The use of the class Hadronic Generator is very simple:
// the constructor needs to be invoked only once - specifying the name
// of the Geant4 "physics case" to consider ("FTFP_BERT" will be
// considered as default is the name is not specified) - and then one
// method needs to be called at each collision, specifying the type of
// collision (hadron, energy, direction, material) to be simulated.
// The class HadronicGenerator is expected to work also in a
// multi-threaded environment with "external" threads (i.e. threads
// that are not necessarily managed by Geant4 run-manager):
// each thread should have its own instance of the class.
//
// See the string "***LOOKHERE***" below for the setting of parameters
// of this example: the "physics case", the set of possibilities from
// which to sample the projectile (i.e. whether the projectile is a
// hadron or an ion - in the case of hadron projectile, a list of hadrons
// is possible from which to sample at each collision; in the case of
// ion projectile, only one type of ion needs to be specified),
// the kinetic energy of the projectile (which can be sampled within
// an interval), whether the direction of the projectile is fixed or
// sampled at each collision, the target material (a list of materials
// is possible, from which the target material can be sampled at each
// collision, and then from this target material, the target nucleus
// will be chosen randomly by Geant4 itself), and whether to print out
// some information or not and how frequently.
// Once a well-defined type of hadron-nucleus or nucleus-nucleus
// inelastic collision has been chosen, the method
//   HadronicGenerator::GenerateInteraction
// returns the secondaries produced by that interaction (in the form
// of a G4VParticleChange object).
// Some information about this final-state is printed out as an example.
//
// Usage:  Hadr09
//------------------------------------------------------------------------

//....oooOO0OOooo........oooOO0OOooo........oooOO0OOooo........oooOO0OOooo......
//....oooOO0OOooo........oooOO0OOooo........oooOO0OOooo........oooOO0OOooo......

#include "CLHEP/Random/Randomize.h"
#include "CLHEP/Random/Ranlux64Engine.h"
#include "G4GenericIon.hh"
#include "G4HadronicParameters.hh"
#include "G4IonTable.hh"
#include "G4Material.hh"
#include "G4NistManager.hh"
#include "G4ParticleTable.hh"
#include "G4PhysicalConstants.hh"
#include "G4ProcessManager.hh"
#include "G4SystemOfUnits.hh"
#include "G4UnitsTable.hh"
#include "G4VParticleChange.hh"
#include "G4ios.hh"
#include "HadronicGenerator-vpgtle.hh"
#include "TAxis.h"
#include "TFile.h"
#include "TGraph.h"
#include "TTree.h"
#include "globals.hh"
#include <TDirectory.h>
#include <TH1D.h>
#include <TH2D.h>
#include <TString.h>
#include <iomanip>
#include <iostream>
#include <numeric>
#include <stdio.h>
#include <stdlib.h>
#include <vector>

using namespace std;

//....oooOO0OOooo........oooOO0OOooo........oooOO0OOooo........oooOO0OOooo......

int main(int argc, char *argv[]) {

  // G4cout << "=== Test of the HadronicGenerator ===" << G4endl;

  // Enable light hypernuclei and anti-hypernuclei
  G4HadronicParameters::Instance()->SetEnableHyperNuclei(false);

  // stw, pro and num are bool that states if options for projectiles
  // type/number and standard computation are activated
  bool stw = false;
  bool pro = false;
  bool num = false;

  G4int numCollisions = 1e4;         // Default number of collisions
  G4String strprojectile = "proton"; // Default projectile type

  // to read the options
  for (int i = 0; i < argc; ++i) {
    std::string arg = argv[i];
    if (arg == "weight") {
      stw = true;
    }
    if (arg == "-n") {
      numCollisions = atoi(argv[i + 1]);
      if (numCollisions <= 0) {
        G4cout << "ERROR: Number of collisions must be a positive integer! 1e4 "
                  "will be used"
               << G4endl;
        numCollisions = 1e4; // Default value
      }
      num = true;
      G4cout << "Number of collisions set to: " << numCollisions << G4endl;
    }
    if (arg == "-p") {
      strprojectile = argv[i + 1];
      pro = true;
      if (strprojectile != "proton" && strprojectile != "neutron") {
        G4cout << "ERROR: Invalid projectile type! Proton will be used."
               << G4endl;
        strprojectile = "proton"; // Default value
      }
      G4cout << "Projectile type set to: " << strprojectile << G4endl;
    }
  }

  // See the HadronicGenerator class for the possibilities and meaning of the
  // "physics cases". ( In short, it is the name of the Geant4 hadronic model
  // used for the simulation of
  //   the collision, with the possibility of having a transition between two
  //   models in a given energy interval, as in physics lists. )
  const G4String namePhysics = "QGSP_BIC_HP";
  const TString physlist = namePhysics;

  // Create the ROOT file and histograms
  TFile *file = new TFile("/path/to/your/stage0/output/test.root", "RECREATE");

  // Set up the parameters for the standard computation
  const std::vector<G4double> Fraction = {
      0.65, 0.185, 0.103, 0.03, 0.015, 0.01, 0.002, 0.002, 0.001, 0.001, 0.001};
  const std::vector<G4String> Body_approx = {"G4_O",  "G4_C",  "G4_H", "G4_N",
                                             "G4_Ca", "G4_P",  "G4_K", "G4_S",
                                             "G4_Na", "G4_Cl", "G4_Mg"};

  // List of elements in the root file.
  const std::vector<G4String> humanBodyElements = {
      //"G4_Al",
      //"G4_Ar",
      //"G4_Be",
      //"G4_B",
      //"G4_Ca",
      "G4_C",
  };
  //"G4_Cl",
  //"G4_Cu",
  //"G4_F",
  //"G4_He",
  //"G4_H",
  //"G4_Li",
  //"G4_Mg",
  //"G4_Ne",
  //"G4_N",
  //"G4_O",};
  //"G4_P",
  //"G4_K",
  //"G4_Si",
  //"G4_Ag",
  //"G4_Na",
  //"G4_S",
  //"G4_Sn",
  //"G4_Ti",
  //"G4_Zn"};

  G4int humanbodyindex =
      humanBodyElements.size(); //***LOOKHERE***  GAP IN PRINTING

  G4ParticleDefinition *projectileNucleus = nullptr;
  G4GenericIon *gion = G4GenericIon::GenericIon();
  gion->SetProcessManager(new G4ProcessManager(gion));
  G4ParticleTable *partTable = G4ParticleTable::GetParticleTable();
  G4IonTable *ions = partTable->GetIonTable();
  partTable->SetReadiness();
  ions->CreateAllIon();
  ions->CreateAllIsomer();

  // The kinetic energy of the projectile will be sampled randomly, with flat
  // probability in the interval [minEnergy, maxEnergy].
  //***LOOKHERE***  HADRON PROJECTILE MAX Ekin
  G4int protonNbBins = 500;
  G4double protonMinEnergy = 0;    // MeV
  G4double protonMaxEnergy = 200.; // MeV
  G4int gammaNbBins = 250;
  G4double gammaMinEnergy = 0;  // MeV
  G4double gammaMaxEnergy = 10; // MeV

  // histogram for the standard weight
  TH1D *TH1D_weight =
      new TH1D("Weight",
               "Weight of the interaction for ToF computing;Protons energy "
               "[MeV];Weight [mm-1]",
               protonNbBins, protonMinEnergy, protonMaxEnergy);

  HadronicGenerator *theHadronicGenerator = new HadronicGenerator(namePhysics);

  if (theHadronicGenerator == nullptr) {
    G4cerr << "ERROR: theHadronicGenerator is NULL !" << G4endl;
    return 1;
  }

  // Loop on the element
  for (G4int k = 0; k < humanbodyindex; k++) {
    G4String done = "not counting in the approximation"; // pre-print for
                                                         // standard computation

    G4String nameMaterial = humanBodyElements[k];
    G4Material *targetMaterial =
        G4NistManager::Instance()->FindOrBuildMaterial(nameMaterial);
    if (targetMaterial == nullptr) {
      G4cerr << "ERROR: Material " << nameMaterial << " is not found !"
             << G4endl;
      return 3;
    }
    const G4Element *targetElement = targetMaterial->GetElement(0);

    TDirectory *dir = file->mkdir(
        targetElement
            ->GetSymbol()); // Création du dossier pour chaque élément chimique

    TString PGbin = to_string(10. / 250);
    TH2D *TH2D_EpEpg =
        new TH2D("EpEpg",
                 "PGs energy as a function of protons;Protons energy [MeV];PGs "
                 "energy [MeV];Log(number of gammas)",
                 protonNbBins, protonMinEnergy, protonMaxEnergy, gammaNbBins,
                 gammaMinEnergy, gammaMaxEnergy); // Graph 2D
    TH2D *TH2D_GammaZ = new TH2D(
        "GammaZ",
        "PG yield per [" + PGbin +
            "MeV*cm];Protons energy [MeV];PGs energy [MeV];Log(GAMMAZ/1)",
        protonNbBins, protonMinEnergy, protonMaxEnergy, gammaNbBins,
        gammaMinEnergy, gammaMaxEnergy); // Graph 2D
    TH1D *TH1D_SigmaInelastic =
        new TH1D("Kapa inelastique",
                 "Linear attenuation coefficient [/cm];Protons energy "
                 "[MeV];kapa inelastique [cm-1]",
                 protonNbBins, protonMinEnergy, protonMaxEnergy);
    TH1D *TH1D_NrPG = new TH1D(
        "NrPG",
        "Number of prompt gamma-rays;Protons energy [MeV];Number of PGs",
        protonNbBins, protonMinEnergy, protonMaxEnergy);

    G4cout << "Loop on element: " << targetElement->GetSymbol() << G4endl;

    // G4DynamicParticle* dynamicProjectile = new G4DynamicParticle(projectile,
    // aDirection, projectileEnergy);

    CLHEP::Ranlux64Engine defaultEngine(1234567, 4);
    CLHEP::HepRandom::setTheEngine(&defaultEngine);
    G4int seed = time(NULL);
    CLHEP::HepRandom::setTheSeed(seed);

    G4int nbPG(0);
    G4int nbCollisions = 1e4; // Default number of collisions
    if (num) {
      nbCollisions = numCollisions;
    }
    G4cout << "Number of collisions: " << nbCollisions << G4endl;
    G4ParticleDefinition *projectile = nullptr;
    if (pro) {
      projectile = partTable->FindParticle(strprojectile);
    } else {
      projectile = partTable->FindParticle("proton");
    }
    G4cout << "Projectile: " << projectile->GetParticleName() << G4endl;
    nbPG = theHadronicGenerator->GenerateInteraction(
        projectile, targetMaterial, TH2D_EpEpg, TH1D_SigmaInelastic,
        TH2D_GammaZ, TH1D_NrPG, nbCollisions);
    if (stw) {
      auto ind =
          std::find(Body_approx.begin(), Body_approx.end(), nameMaterial);
      // Check if the element was found
      if (ind != Body_approx.end()) {
        // Calculate the index
        size_t index = std::distance(Body_approx.begin(), ind);
        done = theHadronicGenerator->WeightCompute(TH2D_GammaZ, TH1D_weight,
                                                   Fraction[index]);
      }
    }

    G4cout << "nr of PG: " << nbPG << G4endl;
    G4cout << nameMaterial << " : " << done << G4endl;
    dir->cd();
    TH2D_EpEpg->Write();
    TH1D_SigmaInelastic->Write();
    TH1D_NrPG->Write();
    TH2D_GammaZ->Write();

    delete TH2D_EpEpg;
    delete TH2D_GammaZ;
    delete TH1D_SigmaInelastic;
    delete TH1D_NrPG;
  }
  if (stw) {
    TDirectory *dirw = file->mkdir("standard_Weight");
    dirw->cd();
    TH1D_weight->Write();
  }
  delete TH1D_weight;

  file->Close();
  delete theHadronicGenerator;

  return 0;
}

//....oooOO0OOooo........oooOO0OOooo........oooOO0OOooo........oooOO0OOooo......
