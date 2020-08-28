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

void init_G4ProductionCutsTable(py::module &);

void init_G4VUserPrimaryGeneratorAction(py::module &);

void init_G4VUserActionInitialization(py::module &);

void init_G4Run(py::module &);

void init_G4UserRunAction(py::module &);

void init_G4Event(py::module &);

void init_G4UserEventAction(py::module &);

void init_G4UserTrackingAction(py::module &);

void init_G4Track(py::module &);

void init_G4Step(py::module &);

void init_G4StepPoint(py::module &);

void init_G4UserSteppingAction(py::module &);

void init_GamTestProtonSource(py::module &);

// geometry/management
void init_G4VSolid(py::module &);

void init_G4VPhysicalVolume(py::module &);

void init_G4PVReplica(py::module &);

void init_G4PVParameterised(py::module &);

void init_G4VNestedParameterisation(py::module &);

void init_G4VPVParameterisation(py::module &);

void init_G4VVolumeMaterialScanner(py::module &);

void init_G4LogicalVolume(py::module &);

void init_G4LogicalVolumeStore(py::module &);

void init_G4GeometryManager(py::module &);

// geometry/solids
void init_G4Box(py::module &);

void init_G4Sphere(py::module &);

void init_G4Trap(py::module &);

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
void init_GamVActor(py::module &);

void init_GamVActorWithSteppingAction(py::module &);

void init_GamSimulationStatisticsActor(py::module &);

void init_GamDoseActor2(py::module &);

void init_GamDoseActor3(py::module &);

void init_itk_image(py::module &);

void init_GamImageNestedParameterisation(py::module &);

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
    init_G4PhysListFactory(m);
    init_G4ProductionCutsTable(m);
    init_G4VUserPrimaryGeneratorAction(m);
    init_G4VUserActionInitialization(m);
    init_G4Run(m);
    init_G4UserRunAction(m);
    init_G4Event(m);
    init_G4UserEventAction(m);
    init_G4UserTrackingAction(m);
    init_G4StepPoint(m);
    init_G4Track(m);
    init_G4Step(m);
    init_G4UserSteppingAction(m);
    init_GamTestProtonSource(m);

    init_G4VSolid(m);
    init_G4VPhysicalVolume(m);
    init_G4PVReplica(m);
    init_G4PVParameterised(m);
    init_G4VPVParameterisation(m);
    init_G4VNestedParameterisation(m);
    init_G4VVolumeMaterialScanner(m);
    init_G4LogicalVolume(m);
    init_G4LogicalVolumeStore(m);
    init_G4GeometryManager(m);

    init_G4Box(m);
    init_G4Sphere(m);
    init_G4Trap(m);

    init_G4PVPlacement(m);
    init_G4TouchableHistory(m);
    init_G4NavigationHistory(m);

    init_G4PhysicsLists(m);

    init_G4VPrimaryGenerator(m);
    init_G4ParticleGun(m);

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
    init_GamVActor(m);
    init_GamVActorWithSteppingAction(m);
    init_GamSimulationStatisticsActor(m);
    init_GamDoseActor2(m);
    init_itk_image(m);
    init_GamDoseActor3(m);
    init_GamImageNestedParameterisation(m);
}
