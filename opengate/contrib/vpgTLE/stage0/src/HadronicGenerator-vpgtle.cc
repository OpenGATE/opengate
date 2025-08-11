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
// * institutes, nor the agencies providing financial support for this *
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
/// \file HadronicGenerator.cc
/// \brief Implementation of the HadronicGenerator class
//
//------------------------------------------------------------------------
// Class: HadronicGenerator
// Author: Alberto Ribon (CERN EP/SFT)
// Date: May 2020
//------------------------------------------------------------------------

//....oooOO0OOooo........oooOO0OOooo........oooOO0OOooo........oooOO0OOooo......
//....oooOO0OOooo........oooOO0OOooo........oooOO0OOooo........oooOO0OOooo......

#include "HadronicGenerator-vpgtle.hh"

#include <algorithm>
#include <iomanip>
#include <iostream>

#include "G4AblaInterface.hh"
#include "G4BGGNucleonInelasticXS.hh"
#include "G4BinaryCascade.hh"
#include "G4BinaryLightIonReaction.hh"
#include "G4Box.hh"
#include "G4CascadeInterface.hh"
#include "G4ComponentGGHadronNucleusXsc.hh"
#include "G4ComponentGGNuclNuclXsc.hh"
#include "G4CrossSectionDataStore.hh"
#include "G4CrossSectionInelastic.hh"
#include "G4DecayPhysics.hh"
#include "G4DynamicParticle.hh"
#include "G4ExcitationHandler.hh"
#include "G4ExcitedStringDecay.hh"
#include "G4FTFModel.hh"
#include "G4GeneratorPrecompoundInterface.hh"
#include "G4HadronInelasticProcess.hh"
#include "G4HadronicInteraction.hh"
#include "G4HadronicParameters.hh"
#include "G4HadronicProcessStore.hh"
#include "G4INCLXXInterface.hh"
#include "G4IonTable.hh"
#include "G4LundStringFragmentation.hh"
#include "G4Material.hh"
#include "G4NeutronInelasticXS.hh"
#include "G4PVPlacement.hh"
#include "G4ParticleTable.hh"
#include "G4PhysicalConstants.hh"
#include "G4PreCompoundModel.hh"
#include "G4ProcessManager.hh"
#include "G4QGSMFragmentation.hh"
#include "G4QGSModel.hh"
#include "G4QGSParticipants.hh"
#include "G4QuasiElasticChannel.hh"
#include "G4StateManager.hh"
#include "G4Step.hh"
#include "G4SystemOfUnits.hh"
#include "G4TheoFSGenerator.hh"
#include "G4TouchableHistory.hh"
#include "G4TransportationManager.hh"
#include "G4UnitsTable.hh"
#include "G4VCrossSectionDataSet.hh"
#include "G4VParticleChange.hh"
#include "G4ios.hh"
#include "globals.hh"

// particle libraries
#include "G4Alpha.hh"
#include "G4Deuteron.hh"
#include "G4He3.hh"
#include "G4Neutron.hh"
#include "G4Proton.hh"
#include "G4Triton.hh"

// HP libraries
#include "G4NeutronCaptureProcess.hh"
#include "G4NeutronHPCapture.hh"
#include "G4NeutronHPCaptureData.hh"
#include "G4NeutronHPElastic.hh"
#include "G4NeutronHPElasticData.hh"
#include "G4NeutronHPFission.hh"
#include "G4NeutronHPFissionData.hh"
#include "G4NeutronHPInelastic.hh"
#include "G4NeutronHPInelasticXS.hh"
#include "G4ParticleHPInelastic.hh"

// root libraries
#include "TH1D.h"
#include "TH2D.h"

#include "G4Element.hh"

//....oooOO0OOooo........oooOO0OOooo........oooOO0OOooo........oooOO0OOooo......

HadronicGenerator::HadronicGenerator(const G4String physicsCase)
    : fPhysicsCase(physicsCase), fLastHadronicProcess(nullptr),
      fPartTable(nullptr) {

  // The constructor set-ups all the particles, models, cross sections and
  // hadronic inelastic processes.
  // This should be done only once for each application.
  // In the case of a multi-threaded application using this class,
  // the constructor should be invoked for each thread,
  // i.e. one instance of the class should be kept per thread.
  // The particles and processes that are created in this constructor
  // will then be used by the method GenerateInteraction at each interaction.
  // Notes:
  // - Neither the hadronic models nor the cross sections are used directly
  //   by the method GenerateInteraction, but they are associated to the
  //   hadronic processes and used by Geant4 to simulate the collision;
  // - Although the class generates only final states, but not free mean paths,
  //   inelastic hadron-nuclear cross sections are needed by Geant4 to sample
  //   the target nucleus from the target material.

  if (fPhysicsCase != "QGSP_BIC_HP") {
    G4cerr
        << "ERROR: Not supported final-state hadronic inelastic physics case !"
        << fPhysicsCase << G4endl
        << "\t Re-try by choosing one of the following:" << G4endl
        << "\t - Hadronic models : QGSP" << G4endl
        << "\t - \"Physics-list proxies\" : QGSP_BIC_HP" << G4endl;
  }

  // Definition of particles
  G4GenericIon *gion = G4GenericIon::Definition();
  gion->SetProcessManager(new G4ProcessManager(gion));
  G4DecayPhysics *decays = new G4DecayPhysics;
  decays->ConstructParticle();
  fPartTable = G4ParticleTable::GetParticleTable();
  fPartTable->SetReadiness();
  G4IonTable *ions = fPartTable->GetIonTable();
  ions->CreateAllIon();
  ions->CreateAllIsomer();

// Building the ElementTable for the NeutronHP model 
// TO BE MODIFIED :: there should be a method in Geant4 for this purpose
  std::vector<G4Element *> myElements;
  myElements.push_back(new G4Element("Hydrogen", "H", 1., 1.01 * g / mole));
  myElements.push_back(new G4Element("Helium", "He", 2., 4.00 * g / mole));
  myElements.push_back(new G4Element("Lithium", "Li", 3., 6.94 * g / mole));
  myElements.push_back(new G4Element("Beryllium", "Be", 4., 9.01 * g / mole));
  myElements.push_back(new G4Element("Boron", "B", 5., 10.81 * g / mole));
  myElements.push_back(new G4Element("Carbon", "C", 6., 12.01 * g / mole));
  myElements.push_back(new G4Element("Nitrogen", "N", 7., 14.01 * g / mole));
  myElements.push_back(new G4Element("Oxygen", "O", 8., 16.00 * g / mole));
  myElements.push_back(new G4Element("Fluorine", "F", 9., 19.00 * g / mole));
  myElements.push_back(new G4Element("Neon", "Ne", 10., 20.18 * g / mole));
  myElements.push_back(new G4Element("Sodium", "Na", 11., 22.99 * g / mole));
  myElements.push_back(new G4Element("Magnesium", "Mg", 12., 24.31 * g / mole));
  myElements.push_back(new G4Element("Aluminium", "Al", 13., 26.98 * g / mole));
  myElements.push_back(new G4Element("Silicon", "Si", 14., 28.09 * g / mole));
  myElements.push_back(new G4Element("Phosphorus", "P", 15., 30.97 * g / mole));
  myElements.push_back(new G4Element("Sulfur", "S", 16., 32.07 * g / mole));
  myElements.push_back(new G4Element("Chlorine", "Cl", 17., 35.45 * g / mole));
  myElements.push_back(new G4Element("Argon", "Ar", 18., 39.95 * g / mole));
  myElements.push_back(new G4Element("Potassium", "K", 19., 39.10 * g / mole));
  myElements.push_back(new G4Element("Calcium", "Ca", 20., 40.08 * g / mole));
  myElements.push_back(new G4Element("Titanium", "Ti", 22., 47.87 * g / mole));
  myElements.push_back(new G4Element("Copper", "Cu", 29., 63.55 * g / mole));
  myElements.push_back(new G4Element("Zinc", "Zn", 30., 65.38 * g / mole));
  myElements.push_back(new G4Element("Silver", "Ag", 47., 107.87 * g / mole));
  myElements.push_back(new G4Element("Tin", "Sn", 50., 118.71 * g / mole));

  // Build BIC model
  G4BinaryCascade *theBICmodel = new G4BinaryCascade;
  G4PreCompoundModel *thePreEquilib =
      new G4PreCompoundModel(new G4ExcitationHandler);
  theBICmodel->SetDeExcitation(thePreEquilib);

  // Build BinaryLightIon model
  G4PreCompoundModel *thePreEquilibBis =
      new G4PreCompoundModel(new G4ExcitationHandler);
  G4BinaryLightIonReaction *theIonBICmodel =
      new G4BinaryLightIonReaction(thePreEquilibBis);

  // HP model
  G4NeutronHPInelastic *theNeutronHP = new G4NeutronHPInelastic;
  theNeutronHP->BuildPhysicsTable(*G4Neutron::Neutron());
  theNeutronHP->SetHadrGenFlag(true); // Enable hadronic generator flag :: due to the ElementTable building default :: TO BE MODIFIED

  // Model instance with constraint to be above a kinetic energy threshold.
  // (Used for ions in all physics lists)
  G4GeneratorPrecompoundInterface *theCascade =
      new G4GeneratorPrecompoundInterface;
  theCascade->SetDeExcitation(thePreEquilib);
  G4LundStringFragmentation *theLundFragmentation =
      new G4LundStringFragmentation;
  G4ExcitedStringDecay *theStringDecay =
      new G4ExcitedStringDecay(theLundFragmentation);
  G4FTFModel *theStringModel = new G4FTFModel;
  theStringModel->SetFragmentationModel(theStringDecay);

  G4TheoFSGenerator *theFTFPmodel_aboveThreshold =
      new G4TheoFSGenerator("FTFP");
  theFTFPmodel_aboveThreshold->SetMaxEnergy(
      G4HadronicParameters::Instance()->GetMaxEnergy());
  theFTFPmodel_aboveThreshold->SetTransport(theCascade);
  theFTFPmodel_aboveThreshold->SetHighEnergyGenerator(theStringModel);

  // Model instance with constraint to be within two kinetic energy thresholds.
  // (Used in the case of QGS-based physics lists for nucleons)
  G4TheoFSGenerator *theFTFPmodel_constrained = new G4TheoFSGenerator("FTFP");
  theFTFPmodel_constrained->SetMaxEnergy(
      G4HadronicParameters::Instance()->GetMaxEnergy());
  theFTFPmodel_constrained->SetTransport(theCascade);
  theFTFPmodel_constrained->SetHighEnergyGenerator(theStringModel);

  // Build the QGSP model
  G4TheoFSGenerator *theQGSPmodel = new G4TheoFSGenerator("QGSP");
  theQGSPmodel->SetMaxEnergy(G4HadronicParameters::Instance()->GetMaxEnergy());
  theQGSPmodel->SetTransport(theCascade);
  G4QGSMFragmentation *theQgsmFragmentation = new G4QGSMFragmentation;
  G4ExcitedStringDecay *theQgsmStringDecay =
      new G4ExcitedStringDecay(theQgsmFragmentation);
  G4VPartonStringModel *theQgsmStringModel = new G4QGSModel<G4QGSParticipants>;
  theQgsmStringModel->SetFragmentationModel(theQgsmStringDecay);
  theQGSPmodel->SetHighEnergyGenerator(theQgsmStringModel);
  G4QuasiElasticChannel *theQuasiElastic =
      new G4QuasiElasticChannel; // QGSP uses quasi-elastic
  theQGSPmodel->SetQuasiElasticChannel(theQuasiElastic);

  // For the case of "physics-list proxies", select the energy range for each
  // hadronic model.
  const G4double ftfpMinE =
      G4HadronicParameters::Instance()->GetMinEnergyTransitionFTF_Cascade();
  const G4double BICMaxE =
      G4HadronicParameters::Instance()->GetMaxEnergyTransitionFTF_Cascade();
  const G4double ftfpMaxE =
      G4HadronicParameters::Instance()->GetMaxEnergyTransitionQGS_FTF();
  const G4double qgspMinE =
      G4HadronicParameters::Instance()->GetMinEnergyTransitionQGS_FTF();

  theBICmodel->SetMaxEnergy(BICMaxE);
  theIonBICmodel->SetMaxEnergy(BICMaxE);
  theFTFPmodel_aboveThreshold->SetMinEnergy(ftfpMinE);
  theFTFPmodel_constrained->SetMinEnergy(ftfpMinE);
  theFTFPmodel_constrained->SetMaxEnergy(ftfpMaxE);
  theQGSPmodel->SetMinEnergy(qgspMinE);

  // Cross sections (needed by Geant4 to sample the target nucleus from the
  // target material)
  G4VCrossSectionDataSet *theProtonXSdata =
      new G4BGGNucleonInelasticXS(G4Proton::Proton());
  theProtonXSdata->BuildPhysicsTable(*(G4Proton::Definition()));

  G4VCrossSectionDataSet *theNeutronXSdata = new G4NeutronInelasticXS;
  theNeutronXSdata->BuildPhysicsTable(*(G4Neutron::Definition()));

  G4VCrossSectionDataSet *theNeutronHPXSdatainel = new G4NeutronHPInelasticXS;
  theNeutronHPXSdatainel->BuildPhysicsTable(*G4Neutron::Definition());

  G4VCrossSectionDataSet *theHyperonsXSdata =
      new G4CrossSectionInelastic(new G4ComponentGGHadronNucleusXsc);

  G4VCrossSectionDataSet *theNuclNuclXSdata =
      new G4CrossSectionInelastic(new G4ComponentGGNuclNuclXsc);

  // Set up inelastic processes : store them in a map (with particle definition
  // as key)
  //                              for convenience

  typedef std::pair<G4ParticleDefinition *, G4HadronicProcess *> ProcessPair;

  G4HadronicProcess *theProtonInelasticProcess =
      new G4HadronInelasticProcess("protonInelastic", G4Proton::Definition());
  fProcessMap.insert(
      ProcessPair(G4Proton::Definition(), theProtonInelasticProcess));

    //a specific processmap is dedidcated to the HP physics for neutron
  G4HadronicProcess *theNeutronHPInelasticProcess =
      new G4HadronInelasticProcess("NeutronHPInelastic",
                                   G4Neutron::Definition());
  fProcessMapHP.insert(
      ProcessPair(G4Neutron::Definition(), theNeutronHPInelasticProcess));

  G4HadronicProcess *theNeutronInelasticProcess =
      new G4HadronInelasticProcess("neutronInelastic", G4Neutron::Definition());
  fProcessMap.insert(
      ProcessPair(G4Neutron::Definition(), theNeutronInelasticProcess));

  // For the HP model, we need to create a new process for the neutron 
  // Prompt-gamma timing with a track-length estimator in proton therapy, JM
  // Létang et al, 2024

  G4HadronicProcess *theDeuteronInelasticProcess =
      new G4HadronInelasticProcess("dInelastic", G4Deuteron::Definition());
  fProcessMap.insert(
      ProcessPair(G4Deuteron::Definition(), theDeuteronInelasticProcess));

  G4HadronicProcess *theTritonInelasticProcess =
      new G4HadronInelasticProcess("tInelastic", G4Triton::Definition());
  fProcessMap.insert(
      ProcessPair(G4Triton::Definition(), theTritonInelasticProcess));

  G4HadronicProcess *theHe3InelasticProcess =
      new G4HadronInelasticProcess("he3Inelastic", G4He3::Definition());
  fProcessMap.insert(ProcessPair(G4He3::Definition(), theHe3InelasticProcess));

  G4HadronicProcess *theAlphaInelasticProcess =
      new G4HadronInelasticProcess("alphaInelastic", G4Alpha::Definition());
  fProcessMap.insert(
      ProcessPair(G4Alpha::Definition(), theAlphaInelasticProcess));

  G4HadronicProcess *theIonInelasticProcess =
      new G4HadronInelasticProcess("ionInelastic", G4GenericIon::Definition());
  fProcessMap.insert(
      ProcessPair(G4GenericIon::Definition(), theIonInelasticProcess));
        
  // Add the cross sections to the corresponding hadronic processes

  // cross-sections for nucleons
  theProtonInelasticProcess->AddDataSet(theProtonXSdata);
  theNeutronInelasticProcess->AddDataSet(theNeutronXSdata);

  // specific cross-sections for neutrons in HP model
  theNeutronHPInelasticProcess->AddDataSet(theNeutronHPXSdatainel);

  // cross-sections for ions
  theDeuteronInelasticProcess->AddDataSet(theNuclNuclXSdata);
  theTritonInelasticProcess->AddDataSet(theNuclNuclXSdata);
  theHe3InelasticProcess->AddDataSet(theNuclNuclXSdata);
  theAlphaInelasticProcess->AddDataSet(theNuclNuclXSdata);
  theIonInelasticProcess->AddDataSet(theNuclNuclXSdata);

  // Register the proper hadronic model(s) to the corresponding hadronic
  // processes. in the physics list QGSP_BIC, BIC is used only for nucleons

  // processes for BIC => mean-energy on nucleons
  theProtonInelasticProcess->RegisterMe(theBICmodel);
  theNeutronInelasticProcess->RegisterMe(theBICmodel);

  // processes for QGSP => High-energy on nucleons
  theProtonInelasticProcess->RegisterMe(theQGSPmodel);
  theNeutronInelasticProcess->RegisterMe(theQGSPmodel);

  // processes for HP => low-energy on neutrons
  theNeutronHPInelasticProcess->RegisterMe(theNeutronHP);

  // processes for ion (BIC for ions)
  theDeuteronInelasticProcess->RegisterMe(theIonBICmodel);
  theTritonInelasticProcess->RegisterMe(theIonBICmodel);
  theHe3InelasticProcess->RegisterMe(theIonBICmodel);
  theAlphaInelasticProcess->RegisterMe(theIonBICmodel);
  theIonInelasticProcess->RegisterMe(theIonBICmodel);

  G4TheoFSGenerator *theFTFPmodelToBeUsed = theFTFPmodel_aboveThreshold;

  theFTFPmodelToBeUsed = theFTFPmodel_constrained;
  theNeutronInelasticProcess->RegisterMe(theFTFPmodelToBeUsed);
  theProtonInelasticProcess->RegisterMe(theFTFPmodelToBeUsed);

  theFTFPmodelToBeUsed = theFTFPmodel_aboveThreshold;
  theDeuteronInelasticProcess->RegisterMe(theFTFPmodelToBeUsed);
  theTritonInelasticProcess->RegisterMe(theFTFPmodelToBeUsed);
  theHe3InelasticProcess->RegisterMe(theFTFPmodelToBeUsed);
  theAlphaInelasticProcess->RegisterMe(theFTFPmodelToBeUsed);
  theIonInelasticProcess->RegisterMe(theFTFPmodelToBeUsed);
}

//....oooOO0OOooo........oooOO0OOooo........oooOO0OOooo........oooOO0OOooo......

HadronicGenerator::~HadronicGenerator() { fPartTable->DeleteAllParticles(); }

//....oooOO0OOooo........oooOO0OOooo........oooOO0OOooo........oooOO0OOooo......

G4int HadronicGenerator::GenerateInteraction(
    G4ParticleDefinition *projectileDefinition, G4Material *targetMaterial,
    TH2D *TH2D_EpEpg, TH1D *TH1D_SigmaInelastic, TH2D *TH2D_GammaZ,
    TH1D *TH1D_NrPG, G4int nbCollisions) {
  // This is the most important method of the HadronicGenerator class:
  // the method performs the specified hadronic interaction
  // (by invoking the "PostStepDoIt" method of the corresponding hadronic
  // process) and returns the final state, i.e. the secondaries produced by the
  // collision. It is a relatively short method because the heavy load of
  // setting up all possible hadronic processes - with their hadronic models,
  // transition regions, and cross sections (the latter is needed for sampling
  // the target nucleus from the target material) - was already done by the
  // constructor of the class.
  G4VParticleChange *aChange = nullptr;
  G4int nbPG(0);

  if (projectileDefinition == nullptr) {
    G4cerr << "ERROR: projectileDefinition is NULL !" << G4endl;
    return 0;
  }

  const G4Element *targetElement = targetMaterial->GetElement(0); //
  G4double molarMass = targetElement->GetA() / (g / mole);

  // Geometry definition (not strictly needed)
  const G4double dimX = 1.0 * mm;
  const G4double dimY = 1.0 * mm;
  const G4double dimZ = 1.0 * mm;
  G4Box *sFrame = new G4Box("Box", dimX, dimY, dimZ);
  G4LogicalVolume *lFrame =
      new G4LogicalVolume(sFrame, targetMaterial, "Box", 0, 0, 0);
  G4PVPlacement *pFrame =
      new G4PVPlacement(0, G4ThreeVector(), "Box", lFrame, 0, false, 0);
  G4TransportationManager::GetTransportationManager()->SetWorldForTracking(
      pFrame);

  G4int numCollisions = nbCollisions; //***LOOKHERE***  NUMBER OF COLLISIONS
  G4double rnd1(0);
  G4double protonEnergy(0), GAMMAZPerRho(0), kappaPerRho(0),
      kappaPerRhoMmCollisions(0);
  G4int Ngamma(0);
  G4double projectileEnergy;
  G4ThreeVector projectileDirection = G4ThreeVector(0.0, 0.0, 1.0);
  G4double CrossSection = 0;

  G4double energyStart = TH1D_SigmaInelastic->GetBinCenter(1) * CLHEP::MeV;
  G4int nbBins = TH1D_SigmaInelastic->GetNbinsX();
  G4double energyEnd = TH1D_SigmaInelastic->GetBinCenter(nbBins) * CLHEP::MeV;
  G4double energyIncrement = TH1D_SigmaInelastic->GetBinWidth(1) * CLHEP::MeV;

  // G4cout << energyStart << " " << energyEnd << " "<< nbBins << " " <<
  // energyIncrement << G4endl;

  // Loop on the energies
  for (G4int f = 1; f <= nbBins; f++) {

    Ngamma = 0;

    // Projectile track & step
    G4DynamicParticle *dParticle = new G4DynamicParticle(
        projectileDefinition, projectileDirection, energyEnd);
    const G4double aTime = 0.0;
    const G4ThreeVector aPosition = G4ThreeVector(0.0, 0.0, 0.0);
    gTrack = new G4Track(dParticle, aTime, aPosition);

    G4Step *step = new G4Step;

    step->SetTrack(gTrack);
    gTrack->SetStep(step);
    aPoint = new G4StepPoint;

    aPoint->SetPosition(aPosition);
    aPoint->SetMaterial(targetMaterial);
    step->SetPreStepPoint(aPoint);
    gTrack->SetStep(step);

    for (G4int i = 0; i < numCollisions; ++i) {

      projectileEnergy = (TH1D_SigmaInelastic->GetBinCenter(f) +
                          (G4UniformRand() - 0.5) * energyIncrement) *
                         CLHEP::MeV;
      // G4cout << "projectile energy = " << projectileEnergy  << G4endl;
      dParticle->SetKineticEnergy(projectileEnergy);
      gTrack->SetKineticEnergy(projectileEnergy);

      // Loop on the collisions
      G4HadronicProcess *theProcess = nullptr;
      G4ParticleDefinition *theProjectileDef = nullptr;
      if (projectileDefinition->IsGeneralIon()) {
        theProjectileDef = G4GenericIon::Definition();
      } else {
        theProjectileDef = projectileDefinition;
      }
        //HP case ??
      if (projectileDefinition == G4Neutron::Neutron() &&
          projectileEnergy < 20 * MeV && projectileEnergy > 4.4 * MeV) {
        // For the HP model, we use the neutron HP inelastic process => specific processmap is used
        auto mapIndex = fProcessMapHP.find(theProjectileDef);
        if (mapIndex != fProcessMapHP.end())
          theProcess = mapIndex->second;
        if (theProcess == nullptr) {
          G4cerr << "ERROR: theProcess is nullptr for neutron HP inelastic !"
                 << G4endl;
        }
      } else {
        auto mapIndex = fProcessMap.find(theProjectileDef);
        if (mapIndex != fProcessMap.end())
          theProcess = mapIndex->second;
        if (theProcess == nullptr) {
          G4cerr << "ERROR: theProcess is nullptr for "
                 << theProjectileDef->GetParticleName() << " inelastic !"
                 << G4endl;
        }
      }
      if (theProcess != nullptr) {
        aChange = theProcess->PostStepDoIt(*gTrack, *step);
      } else {
        G4cerr << "ERROR: theProcess is nullptr !" << G4endl;
      }
      fLastHadronicProcess = theProcess;
      CrossSection = GetCrossSection(dParticle, targetElement, targetMaterial);
      kappaPerRho = (CrossSection * Avogadro) / molarMass;
      // The assumption in the prompt-gamma TLE is to use the defaut distance
      // unit, ie mm
      // ($G4_DIR/src/source/externals/clhep/include/CLHEP/Units/SystemOfUnits.h)
      kappaPerRhoMmCollisions = kappaPerRho / (numCollisions * cm);

      G4int nsec = aChange ? aChange->GetNumberOfSecondaries() : 0;

      // Loop over produced secondaries and eventually print out some
      // information.
      for (G4int j = 0; j < nsec; ++j) {
        const G4DynamicParticle *sec =
            aChange->GetSecondary(j)->GetDynamicParticle();
        const G4String g = sec->GetDefinition()->GetParticleName();
        Double_t E = 0;

        if (g == "gamma") {
          Ngamma++;
          nbPG++;
          E = sec->GetKineticEnergy();
          if (E > 0.04 * MeV) {
            TH2D_GammaZ->Fill(projectileEnergy, E, kappaPerRhoMmCollisions);
            TH2D_EpEpg->Fill(projectileEnergy, E);
          }
        }
        delete aChange->GetSecondary(j);
      }
      if (aChange)
        aChange->Clear();
      // delete dynamicProjectile;
    }

    dParticle->SetKineticEnergy(TH1D_SigmaInelastic->GetBinCenter(f) *
                                CLHEP::MeV);
    CrossSection = GetCrossSection(dParticle, targetElement, targetMaterial);
    kappaPerRho = (CrossSection * Avogadro) / molarMass;
    TH1D_SigmaInelastic->SetBinContent(f, kappaPerRho);
    TH1D_NrPG->SetBinContent(f, Ngamma);

    delete step;
    delete dParticle;
  }

  delete pFrame;
  delete lFrame;
  delete sFrame;

  return nbPG;
}

//....oooOO0OOooo........oooOO0OOooo........oooOO0OOooo........oooOO0OOooo......

G4double HadronicGenerator::GetCrossSection(const G4DynamicParticle *part,
                                            const G4Element *elm,
                                            const G4Material *targetMaterial) {
  G4double CrossSection = -999;
  G4HadronicProcess *hadProcess = GetHadronicProcess();
  const G4double squareCentimeter = cm * cm;
  const G4ParticleDefinition *particle = part->GetParticleDefinition();

  // Récupérer la section efficace
  CrossSection = hadProcess->GetCrossSectionDataStore()->GetCrossSection(
      part, elm, targetMaterial);

  return CrossSection / squareCentimeter;
}

//....oooOO0OOooo........oooOO0OOooo........oooOO0OOooo........oooOO0OOooo......

G4String HadronicGenerator::WeightCompute(TH2D *TH2D_GammaZ, TH1D *TH1D_weight,
                                          G4double frac) {
  // This method computes the weight of the interaction for ToF computing
  // and returns a string with the result.
  // The weight is computed as the ratio of the number of gammas per bin
  // to the number of collisions per bin.
  G4String result = "is counted, with a fraction of " + std::to_string(frac);

  G4int nbBins = TH2D_GammaZ->GetNbinsX();
  for (G4int i = 1; i <= nbBins; ++i) {
    // Sum the column at index i
    G4double columnSum =
        TH2D_GammaZ->Integral(i, i, 1, TH2D_GammaZ->GetNbinsY());
    // Store the sum in the TH1D histogram
    TH1D_weight->SetBinContent(i, TH1D_weight->GetBinContent(i) +
                                      frac * columnSum);
    std::cout << "Column " << i << " sum: " << TH1D_weight->GetBinContent(i)
              << std::endl;
  }

  return result;
}

//....oooOO0OOooo........oooOO0OOooo........oooOO0OOooo........oooOO0OOooo......
