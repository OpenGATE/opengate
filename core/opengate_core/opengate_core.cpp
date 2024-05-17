/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#include "g4_bindings/GateConfiguration.h"
#include <pybind11/pybind11.h>

namespace py = pybind11;

// management
void init_G4ThreeVector(py::module &);

void init_G4AffineTransform(py::module &);

void init_G4String(py::module &);

void init_G4RotationMatrix(py::module &);

void init_G4Transform3D(py::module &);

void init_G4UnitsTable(py::module &);

void init_G4Threading(py::module &);

// CLHEP
void init_Randomize(py::module &);

// materials
void init_G4NistManager(py::module &);

void init_G4Material(py::module &);

void init_G4Element(py::module &);

void init_G4IonisParamMat(py::module &);

void init_G4MaterialPropertiesTable(py::module &);

// surfaces

void init_G4OpticalSurface(py::module &);
void init_G4LogicalBorderSurface(py::module &);

// run
void init_G4RunManager(py::module &);

void init_WrappedG4RunManager(py::module &);

void init_G4RunManagerFactory(py::module &);

void init_G4MTRunManager(py::module &);

void init_WrappedG4MTRunManager(py::module &);

void init_G4StateManager(py::module &);

void init_G4VUserDetectorConstruction(py::module &);

void init_G4VUserParallelWorld(py::module &);

void init_G4VUserPhysicsList(py::module &);

void init_G4ParallelWorldPhysics(py::module &);

void init_G4VModularPhysicsList(py::module &);

void init_G4VPhysicsConstructor(py::module &);

void init_G4PhysicsFreeVector(py::module &);

void init_G4VUserPrimaryGeneratorAction(py::module &);

void init_G4VUserActionInitialization(py::module &);

void init_G4Run(py::module &);

void init_G4UserRunAction(py::module &);

void init_G4Event(py::module &);

void init_G4PrimaryVertex(py::module &);

void init_G4UserEventAction(py::module &);

void init_G4UserTrackingAction(py::module &);

void init_G4UserStackingAction(py::module &);

void init_G4UserSteppingAction(py::module &);

void init_G4Track(py::module &);

void init_G4Step(py::module &);

void init_G4StepPoint(py::module &);

// processes/electromagnetic/utils

void init_G4EmParameters(py::module &);

void init_G4PixeCrossSectionHandler(py::module &);

void init_G4PixeShellDataSet(py::module &);

void init_G4IInterpolator(py::module &);

void init_G4LinInterpolator(py::module &);

void init_G4DataVector(py::module &);

// processes/hadronic/models/radioactive_decay

void init_G4RadioactiveDecay(py::module &);

// processes/cuts

void init_G4VProcess(py::module &);

void init_G4ProcessTable(py::module &);

void init_G4ProcessVector(py::module &);

void init_G4VRestDiscreteProcess(py::module &);

void init_G4ProcessManager(py::module &);

void init_G4ProductionCutsTable(py::module &);

void init_G4ProductionCuts(py::module &);

void init_G4UserLimits(py::module &);

void init_G4StepLimiterPhysics(py::module &);

void init_G4StepLimiter(py::module &);

void init_G4UserSpecialCuts(py::module &);

// geometry/management

void init_G4VSolid(py::module &);

void init_G4VPhysicalVolume(py::module &);

void init_G4PVReplica(py::module &);

void init_G4PVParameterised(py::module &);

void init_G4VNestedParameterisation(py::module &);

void init_G4VVolumeMaterialScanner(py::module &);

void init_G4VPVParameterisation(py::module &);

void init_G4LogicalVolume(py::module &);

void init_G4LogicalVolumeStore(py::module &);

void init_G4PhysicalVolumeStore(py::module &);

void init_G4GeometryManager(py::module &);

void init_G4Region(py::module &);

void init_G4RegionStore(py::module &);

// geometry/solids
void init_G4Box(py::module &);

void init_G4Polyhedra(py::module &);

void init_G4Sphere(py::module &);

void init_G4Trap(py::module &);

void init_G4Tubs(py::module &);

void init_G4Cons(py::module &);

void init_G4Trd(py::module &);

void init_G4MultiUnion(py::module &);

void init_G4SubtractionSolid(py::module &);

void init_G4UnionSolid(py::module &);

void init_G4IntersectionSolid(py::module &);

void init_G4VFacet(py::module &m);

void init_G4TessellatedSolid(py::module &m);

void init_G4TriangularFacet(py::module &m);

void init_G4QuadrangularFacet(py::module &m);

// geometry/volume
void init_G4PVPlacement(py::module &);

void init_G4TouchableHistory(py::module &);

void init_G4NavigationHistory(py::module &);

void init_G4Navigator(py::module &);

// specific to python
void init_G4PhysicsLists(py::module &);

void init_G4PhysListFactory(py::module &);

// event
void init_G4ParticleGun(py::module &);

void init_G4VPrimaryGenerator(py::module &);

void init_G4SPSPosDistribution(py::module &);

void init_GateSPSPosDistribution(py::module &);

void init_GateSPSVoxelsPosDistribution(py::module &);

void init_G4SPSAngDistribution(py::module &);

void init_G4SPSRandomGenerator(py::module &);

void init_G4SPSEneDistribution(py::module &);

void init_G4SingleParticleSource(py::module &);

// particles/management
void init_G4ParticleTable(py::module &);

void init_G4ParticleDefinition(py::module &);

void init_G4Ions(py::module &);

void init_G4IonTable(py::module &);

void init_G4DecayTable(py::module &);

void init_G4VDecayChannel(py::module &);

// tracking
void init_G4VSteppingVerbose(py::module &);

// digit_hits
void init_G4VPrimitiveScorer(py::module &);

// intercoms
void init_G4UImanager(py::module &);

void init_G4UIsession(py::module &);

// visualisation/management

void init_G4VisManager(py::module &);

void init_G4VisExecutive(py::module &);

// graphics_rep

void init_G4VisAttributes(py::module &);

// interfaces

void init_G4UIExecutive(py::module &);

void init_G4UIQt(py::module &);

void init_QMainWindow(py::module &);

// Gate
void init_GateCheckDeex(py::module &);

void init_GateInfo(py::module &);

void init_GateVActor(py::module &);

void init_GateActorManager(py::module &);

void init_GateVFilter(py::module &);

void init_GateParticleFilter(py::module &);

void init_GateThresholdAttributeFilter(py::module &);

void init_GateTrackCreatorProcessFilter(py::module &);

void init_GateKineticEnergyFilter(py::module &);

void init_GateDoseActor(py::module &m);

void init_GateFluenceActor(py::module &m);

void init_GateLETActor(py::module &m);

void init_GateChemistryActor(py::module &m);

void init_GateChemistryLongTimeActor(py::module &m);

void init_GateARFActor(py::module &m);

void init_GateARFTrainingDatasetActor(py::module &m);

void init_GateKillActor(py::module &);

void init_itk_image(py::module &);

void init_GateImageNestedParameterisation(py::module &);

void init_GateRepeatParameterisation(py::module &);

void init_GateSourceManager(py::module &);

void init_GateGenericSource(py::module &);

void init_GateTreatmentPlanPBSource(py::module &);

void init_GateTemplateSource(py::module &);

void init_GatePencilBeamSource(py::module &m);

void init_GateVoxelsSource(py::module &);

void init_GateGANSource(py::module &);

void init_GatePhaseSpaceSource(py::module &);

void init_GateGANPairSource(py::module &);

void init_GateRunAction(py::module &);

void init_GateEventAction(py::module &);

void init_GateTrackingAction(py::module &);

void init_GateStackingAction(py::module &);

void init_GateSimulationStatisticsActor(py::module &);

void init_GatePhaseSpaceActor(py::module &);

// void init_GateComptonSplittingActor(py::module &);

void init_GateOptrComptSplittingActor(py::module &m);

void init_GateBOptrBremSplittingActor(py::module &m);

void init_G4VBiasingOperator(py::module &m);

void init_GateHitsCollectionActor(py::module &);

void init_GateMotionVolumeActor(py::module &);

void init_GateHitsAdderActor(py::module &);

void init_GateDigitizerReadoutActor(py::module &m);

void init_GateDigitizerBlurringActor(py::module &m);

void init_GateDigitizerEfficiencyActor(py::module &m);

void init_GateDigitizerSpatialBlurringActor(py::module &m);

void init_GateDigitizerEnergyWindowsActor(py::module &m);

void init_GateDigitizerProjectionActor(py::module &m);

void init_GateDigiAttributeManager(py::module &m);

void init_GateVDigiAttribute(py::module &m);

void init_GateVSource(py::module &);

void init_GateExceptionHandler(py::module &);

void init_GateNTuple(py::module &);

void init_GateHelpers(py::module &);

void init_GateUniqueVolumeIDManager(py::module &);

void init_GateUniqueVolumeID(py::module &);

void init_GateVolumeDepthID(py::module &m);

PYBIND11_MODULE(opengate_core, m) {

  init_G4ThreeVector(m);
  init_G4AffineTransform(m);
  init_G4String(m);
  init_G4RotationMatrix(m);
  init_G4Transform3D(m);
  init_G4UnitsTable(m);
  init_G4Threading(m);

  init_Randomize(m);

  init_G4NistManager(m);
  init_G4Material(m);
  init_G4Element(m);
  init_G4IonisParamMat(m);
  init_G4MaterialPropertiesTable(m);

  init_G4VSteppingVerbose(m);

  init_G4RunManager(m);
  init_WrappedG4RunManager(m);
  init_G4MTRunManager(m);
  init_WrappedG4MTRunManager(m);
  init_G4RunManagerFactory(m);
  init_G4StateManager(m);
  init_G4VUserDetectorConstruction(m);

  init_G4VUserPhysicsList(m);
  init_G4VPhysicsConstructor(m);
  init_G4VModularPhysicsList(m);
  init_G4PhysListFactory(m);
  init_G4PhysicsFreeVector(m);

  init_G4VUserParallelWorld(m);
  init_G4ParallelWorldPhysics(m);

  init_G4VUserPrimaryGeneratorAction(m);
  init_G4VUserActionInitialization(m);
  init_G4Run(m);
  init_G4UserRunAction(m);

  init_G4Event(m);
  init_G4PrimaryVertex(m);
  init_G4UserEventAction(m);
  init_G4UserTrackingAction(m);
  init_G4UserStackingAction(m);
  init_G4StepPoint(m);
  init_G4Track(m);
  init_G4Step(m);
  init_G4UserSteppingAction(m);

  init_G4VSolid(m);
  init_G4VFacet(m);
  init_G4VPhysicalVolume(m);
  init_G4PVReplica(m);
  init_G4VVolumeMaterialScanner(m);
  init_G4PVParameterised(m);
  init_G4VPVParameterisation(m);
  init_G4VNestedParameterisation(m);
  init_G4LogicalVolume(m);
  init_G4LogicalVolumeStore(m);
  init_G4PhysicalVolumeStore(m);
  init_G4GeometryManager(m);

  init_G4OpticalSurface(m);
  init_G4LogicalBorderSurface(m);

  init_G4Region(m);
  init_G4RegionStore(m);

  init_G4Box(m);
  init_G4Polyhedra(m);
  init_G4Sphere(m);
  init_G4Trap(m);
  init_G4Tubs(m);
  init_G4Cons(m);
  init_G4Trd(m);
  init_G4MultiUnion(m);
  init_G4SubtractionSolid(m);
  init_G4UnionSolid(m);
  init_G4IntersectionSolid(m);
  init_G4TessellatedSolid(m);
  init_G4TriangularFacet(m);
  init_G4QuadrangularFacet(m);

  init_G4PVPlacement(m);
  init_G4TouchableHistory(m);
  init_G4NavigationHistory(m);
  init_G4Navigator(m);

  init_G4PhysicsLists(m);
  init_G4EmParameters(m);
  init_G4PixeCrossSectionHandler(m);
  init_G4PixeShellDataSet(m);
  init_G4IInterpolator(m);
  init_G4LinInterpolator(m);
  init_G4DataVector(m);

  init_G4VProcess(m);
  init_G4VBiasingOperator(m);
  init_G4ProcessManager(m);
  init_G4ProcessTable(m);
  init_G4ProcessVector(m);
  init_G4VRestDiscreteProcess(m);

  init_G4ProductionCuts(m);
  init_G4ProductionCutsTable(m);
  init_G4UserLimits(m);
  init_G4StepLimiter(m);
  init_G4StepLimiterPhysics(m);
  init_G4UserSpecialCuts(m);

  init_G4RadioactiveDecay(m); // must be after init_G4VRestDiscreteProcess

  init_G4VPrimaryGenerator(m);
  init_G4ParticleGun(m);
  init_G4SPSPosDistribution(m);
  init_G4SPSAngDistribution(m);
  init_G4SPSRandomGenerator(m);
  init_G4SPSEneDistribution(m);
  init_G4SingleParticleSource(m);

  init_G4ParticleTable(m);
  init_G4ParticleDefinition(m);
  init_G4Ions(m);
  init_G4IonTable(m);
  init_G4DecayTable(m);
  init_G4VDecayChannel(m);

  init_G4VPrimitiveScorer(m);

  init_G4UImanager(m);
  init_G4UIsession(m);

  init_G4VisManager(m);
  init_G4VisExecutive(m);
  init_G4VisAttributes(m);

  // interfaces
#if DUSE_USE_VISU > 0
  init_QMainWindow(m);
  init_G4UIExecutive(m);
  init_G4UIQt(m);
#endif

  // Gate
  init_GateCheckDeex(m);
  init_GateInfo(m);
  init_GateVActor(m);
  init_GateActorManager(m);
  init_GateVFilter(m);
  init_GateParticleFilter(m);
  init_GateTrackCreatorProcessFilter(m);
  init_GateKineticEnergyFilter(m);
  init_GateThresholdAttributeFilter(m);
  init_itk_image(m);
  init_GateImageNestedParameterisation(m);
  init_GateRepeatParameterisation(m);
  init_GateVSource(m);
  init_GateSourceManager(m);
  init_GateGenericSource(m);
  init_GateTreatmentPlanPBSource(m);
  init_GateTemplateSource(m);
  init_GatePencilBeamSource(m);
  init_GateVoxelsSource(m);
  init_GateGANSource(m);
  init_GatePhaseSpaceSource(m);
  init_GateGANPairSource(m);
  init_GateSPSPosDistribution(m);
  init_GateSPSVoxelsPosDistribution(m);
  init_GateRunAction(m);
  init_GateEventAction(m);
  init_GateTrackingAction(m);
  init_GateStackingAction(m);
  init_GateDoseActor(m);
  init_GateFluenceActor(m);
  init_GateLETActor(m);
  init_GateChemistryActor(m);
  init_GateChemistryLongTimeActor(m);
  init_GateSimulationStatisticsActor(m);
  init_GatePhaseSpaceActor(m);
  // init_GateComptonSplittingActor(m);
  init_GateBOptrBremSplittingActor(m);
  init_GateOptrComptSplittingActor(m);
  init_GateHitsCollectionActor(m);
  init_GateMotionVolumeActor(m);
  init_GateHitsAdderActor(m);
  init_GateDigitizerReadoutActor(m);
  init_GateDigitizerBlurringActor(m);
  init_GateDigitizerEfficiencyActor(m);
  init_GateDigitizerSpatialBlurringActor(m);
  init_GateDigitizerEnergyWindowsActor(m);
  init_GateDigitizerProjectionActor(m);
  init_GateARFActor(m);
  init_GateARFTrainingDatasetActor(m);
  init_GateKillActor(m);
  init_GateDigiAttributeManager(m);
  init_GateVDigiAttribute(m);
  init_GateExceptionHandler(m);
  init_GateNTuple(m);
  init_GateHelpers(m);
  init_GateUniqueVolumeIDManager(m);
  init_GateUniqueVolumeID(m);
  init_GateVolumeDepthID(m);
}
