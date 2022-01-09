/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#include <pybind11/pybind11.h>
#include "g4_bindings/GamConfiguration.h"

namespace py = pybind11;

// management
void init_G4ThreeVector(py::module &);

void init_G4AffineTransform(py::module &);

void init_G4String(py::module &);

void init_G4RotationMatrix(py::module &);

void init_G4Transform3D(py::module &);

void init_G4UnitsTable(py::module &);

// CLHEP
void init_Randomize(py::module &);

// materials
void init_G4NistManager(py::module &);

void init_G4Material(py::module &);

void init_G4Element(py::module &);

void init_G4IonisParamMat(py::module &);

// run
void init_G4RunManager(py::module &);

void init_G4MTRunManager(py::module &);

void init_G4VUserDetectorConstruction(py::module &);

void init_G4VUserPhysicsList(py::module &);

void init_G4VModularPhysicsList(py::module &);

void init_G4VPhysicsConstructor(py::module &);

void init_G4VUserPrimaryGeneratorAction(py::module &);

void init_G4VUserActionInitialization(py::module &);

void init_G4Run(py::module &);

void init_G4UserRunAction(py::module &);

void init_G4Event(py::module &);

void init_G4PrimaryVertex(py::module &);

void init_G4UserEventAction(py::module &);

void init_G4UserTrackingAction(py::module &);

void init_G4UserSteppingAction(py::module &);

void init_G4Track(py::module &);

void init_G4Step(py::module &);

void init_G4StepPoint(py::module &);

// processes/electromagnetic/utils
void init_G4EmParameters(py::module &);

// processes/cuts

void init_G4ProductionCutsTable(py::module &);

void init_G4ProductionCuts(py::module &);

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

void init_G4MultiUnion(py::module &);

void init_G4SubtractionSolid(py::module &);

void init_G4UnionSolid(py::module &);

void init_G4IntersectionSolid(py::module &);

// geometry/volume
void init_G4PVPlacement(py::module &);

void init_G4TouchableHistory(py::module &);

void init_G4NavigationHistory(py::module &);

// specific to python 
void init_G4PhysicsLists(py::module &);

void init_G4PhysListFactory(py::module &);

// event
void init_G4ParticleGun(py::module &);

void init_G4VPrimaryGenerator(py::module &);

void init_G4SPSPosDistribution(py::module &);

void init_GamSPSPosDistribution(py::module &);

void init_GamSPSVoxelsPosDistribution(py::module &);

void init_G4SPSAngDistribution(py::module &);

void init_G4SPSRandomGenerator(py::module &);

void init_G4SPSEneDistribution(py::module &);

void init_G4SingleParticleSource(py::module &);

// particles/management
void init_G4ParticleTable(py::module &);

void init_G4ParticleDefinition(py::module &);

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

// Gam
void init_GamInfo(py::module &);

void init_GamVActor(py::module &);

void init_GamVFilter(py::module &);

void init_GamParticleFilter(py::module &);

void init_GamDoseActor(py::module &m);

void init_itk_image(py::module &);

void init_GamImageNestedParameterisation(py::module &);

void init_GamSourceManager(py::module &);

void init_GamGenericSource(py::module &);

void init_GamVoxelsSource(py::module &);

void init_GamRunAction(py::module &);

void init_GamEventAction(py::module &);

void init_GamTrackingAction(py::module &);

void init_GamSimulationStatisticsActor(py::module &);

void init_GamPhaseSpaceActor2(py::module &);

void init_GamHitsCollectionActor(py::module &);

void init_GamHitsAdderActor(py::module &);

void init_GamHitAttributeManager(py::module &);

void init_GamVHitAttribute(py::module &);


void init_GamVSource(py::module &);

void init_GamExceptionHandler(py::module &);

void init_GamNTuple(py::module &);

PYBIND11_MODULE(gam_g4, m) {

    init_G4ThreeVector(m);
    init_G4AffineTransform(m);
    init_G4String(m);
    init_G4RotationMatrix(m);
    init_G4Transform3D(m);
    init_G4UnitsTable(m);

    init_Randomize(m);

    init_G4NistManager(m);
    init_G4Material(m);
    init_G4Element(m);
    init_G4IonisParamMat(m);

    init_G4VSteppingVerbose(m);

    init_G4RunManager(m);
    init_G4MTRunManager(m);
    init_G4VUserDetectorConstruction(m);
    init_G4VUserPhysicsList(m);
    init_G4VModularPhysicsList(m);
    init_G4VPhysicsConstructor(m);
    init_G4PhysListFactory(m);
    init_G4VUserPrimaryGeneratorAction(m);
    init_G4VUserActionInitialization(m);
    init_G4Run(m);
    init_G4UserRunAction(m);
    init_G4Event(m);
    init_G4PrimaryVertex(m);
    init_G4UserEventAction(m);
    init_G4UserTrackingAction(m);
    init_G4StepPoint(m);
    init_G4Track(m);
    init_G4Step(m);
    init_G4UserSteppingAction(m);

    init_G4VSolid(m);
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

    init_G4Region(m);
    init_G4RegionStore(m);

    init_G4Box(m);
    init_G4Polyhedra(m);
    init_G4Sphere(m);
    init_G4Trap(m);
    init_G4Tubs(m);
    init_G4Cons(m);
    init_G4MultiUnion(m);
    init_G4SubtractionSolid(m);
    init_G4UnionSolid(m);
    init_G4IntersectionSolid(m);

    init_G4PVPlacement(m);
    init_G4TouchableHistory(m);
    init_G4NavigationHistory(m);

    init_G4PhysicsLists(m);
    init_G4EmParameters(m);

    init_G4ProductionCuts(m);
    init_G4ProductionCutsTable(m);

    init_G4VPrimaryGenerator(m);
    init_G4ParticleGun(m);
    init_G4SPSPosDistribution(m);
    init_G4SPSAngDistribution(m);
    init_G4SPSRandomGenerator(m);
    init_G4SPSEneDistribution(m);
    init_G4SingleParticleSource(m);

    init_G4ParticleTable(m);
    init_G4ParticleDefinition(m);

    init_G4VPrimitiveScorer(m);

    init_G4UImanager(m);
    init_G4UIsession(m);

    init_G4VisManager(m);
    init_G4VisExecutive(m);
    init_G4VisAttributes(m);

    // interfaces
    init_QMainWindow(m);
    init_G4UIExecutive(m);
    init_G4UIQt(m);

    // Gam // FIXME will be modified
    init_GamInfo(m);
    init_GamVActor(m);
    init_GamVFilter(m);
    init_GamParticleFilter(m);
    init_itk_image(m);
    init_GamDoseActor(m);
    init_GamImageNestedParameterisation(m);
    init_GamVSource(m);
    init_GamSourceManager(m);
    init_GamGenericSource(m);
    init_GamVoxelsSource(m);
    init_GamSPSPosDistribution(m);
    init_GamSPSVoxelsPosDistribution(m);
    init_GamRunAction(m);
    init_GamEventAction(m);
    init_GamTrackingAction(m);
    init_GamSimulationStatisticsActor(m);
    init_GamPhaseSpaceActor2(m);
    init_GamHitsCollectionActor(m);
    init_GamHitsAdderActor(m);
    init_GamHitAttributeManager(m);
    init_GamVHitAttribute(m);
    init_GamExceptionHandler(m);
    init_GamNTuple(m);
}
