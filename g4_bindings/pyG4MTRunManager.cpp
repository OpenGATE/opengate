/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */
#include <pybind11/pybind11.h>

#include "G4MTRunManager.hh"
#include "G4RunManager.hh"
#include "G4VUserDetectorConstruction.hh"
#include "G4VUserPrimaryGeneratorAction.hh"
#include "G4VUserPhysicsList.hh"
#include "G4VUserActionInitialization.hh"

namespace py = pybind11;

void init_G4MTRunManager(py::module &m) {

    // No destructor for this singleton class because seg fault from py side
    py::class_<G4MTRunManager, std::unique_ptr<G4MTRunManager, py::nodelete>>(m, "G4MTRunManager")
            .def(py::init())
            .def_static("GetRunManager", &G4MTRunManager::GetRunManager, py::return_value_policy::reference)


                    //.def("Initialize", &G4MTRunManager::Initialize)
            .def("Initialize", [](G4MTRunManager *mt) {
                std::cout << "GAM_G4 G4MTRunManager::Initialize" << std::endl;
                py::gil_scoped_release release;
                std::cout << "after gil_scoped_release" << std::endl;
                mt->Initialize();
                std::cout << "END GAM_G4 G4MTRunManager::Initialize" << std::endl;
            })

            .def("SetNumberOfThreads", &G4MTRunManager::SetNumberOfThreads)
            .def("GetNumberOfThreads", &G4MTRunManager::GetNumberOfThreads)
            .def("RestoreRandomNumberStatus", &G4MTRunManager::RestoreRandomNumberStatus)

            .def("SetUserInitialization",
                 py::overload_cast<G4VUserDetectorConstruction *>(&G4MTRunManager::SetUserInitialization))
            .def("SetUserInitialization",
                 py::overload_cast<G4VUserPhysicsList *>(&G4MTRunManager::SetUserInitialization))
            .def("SetUserInitialization",
                 py::overload_cast<G4VUserActionInitialization *>(&G4MTRunManager::SetUserInitialization))
            .def("SetUserAction",
                 py::overload_cast<G4VUserPrimaryGeneratorAction *>(&G4MTRunManager::SetUserAction))

            .def("SetVerboseLevel", &G4MTRunManager::SetVerboseLevel)
            .def("GetVerboseLevel", &G4MTRunManager::GetVerboseLevel)
            .def("Initialize", &G4MTRunManager::Initialize)

            .def("BeamOn", &G4MTRunManager::BeamOn) // warning MT

            .def("AbortRun", &G4RunManager::AbortRun)
            .def("ConfirmBeamOnCondition", &G4RunManager::ConfirmBeamOnCondition)
            .def("RunTermination", &G4RunManager::RunTermination)
            .def("TerminateEventLoop", &G4RunManager::TerminateEventLoop)
            .def("RunInitialization", &G4RunManager::RunInitialization)

            .def("InitializeGeometry", &G4RunManager::InitializeGeometry)
            .def("InitializePhysics", &G4RunManager::InitializePhysics)



        /*

        // ---
        .def("SetUserInitialization", f1_SetUserInitialization)
        .def("SetUserInitialization", f2_SetUserInitialization)
        .def("SetUserAction",         f1_SetUserAction)
        .def("SetUserAction",         f2_SetUserAction)
        .def("SetUserAction",         f3_SetUserAction)
        .def("SetUserAction",         f4_SetUserAction)
        .def("SetUserAction",         f5_SetUserAction)
        .def("SetUserAction",         f6_SetUserAction)
        // ---
        .def("GetUserDetectorConstruction",
        &G4MTRunManager::GetUserDetectorConstruction,
        return_internal_reference<>())
        .def("GetUserPhysicsList",
        &G4MTRunManager::GetUserPhysicsList,
        return_internal_reference<>())
        .def("GetUserPrimaryGeneratorAction",
        &G4MTRunManager::GetUserPrimaryGeneratorAction,
        return_internal_reference<>())
        .def("GetUserRunAction",      &G4MTRunManager::GetUserRunAction,
        return_internal_reference<>())
        .def("GetUserEventAction",    &G4MTRunManager::GetUserEventAction,
        return_internal_reference<>())
        .def("GetUserStackingAction", &G4MTRunManager::GetUserStackingAction,
        return_internal_reference<>())
        .def("GetUserTrackingAction", &G4MTRunManager::GetUserTrackingAction,
        return_internal_reference<>())
        .def("GetUserSteppingAction", &G4MTRunManager::GetUserSteppingAction,
        return_internal_reference<>())
        // ---
        .def("AbortRun",             &G4MTRunManager::AbortRun,
        f_AbortRun((arg("soft_abort")=false),
        "Abort run (event loop)."))
        .def("AbortEvent",           &G4MTRunManager::AbortEvent)
        .def("DefineWorldVolume",    &G4MTRunManager::DefineWorldVolume,
        f_DefineWorldVolume())
        .def("DumpRegion",           f1_DumpRegion)
        .def("DumpRegion",           f2_DumpRegion, f_DumpRegion())
        .def("rndmSaveThisRun",      &G4MTRunManager::rndmSaveThisRun)
        .def("rndmSaveThisEvent",    &G4MTRunManager::rndmSaveThisEvent)
        .def("RestoreRandomNumberStatus",
        &G4MTRunManager::RestoreRandomNumberStatus)
        .def("SetRandomNumberStore", &G4MTRunManager::SetRandomNumberStore)
        .def("GetRandomNumberStore", &G4MTRunManager::GetRandomNumberStore)
        .def("SetRandomNumberStoreDir", &G4MTRunManager::SetRandomNumberStoreDir)
        .def("GeometryHasBeenModified", &G4MTRunManager::GeometryHasBeenModified,
        f_GeometryHasBeenModified())
        .def("PhysicsHasBeenModified",  &G4MTRunManager::PhysicsHasBeenModified)
        .def("GetGeometryToBeOptimized",&G4MTRunManager::GetGeometryToBeOptimized)
        .def("GetCurrentRun",  &G4MTRunManager::GetCurrentRun,
        return_value_policy<reference_existing_object>())
        .def("GetCurrentEvent", &G4MTRunManager::GetCurrentEvent,
        return_value_policy<reference_existing_object>())
        .def("SetRunIDCounter",        &G4MTRunManager::SetRunIDCounter)
        .def("GetVersionString",     &G4MTRunManager::GetVersionString,
        return_value_policy<reference_existing_object>())
        .def("GetRandomNumberStoreDir", &G4MTRunManager::GetRandomNumberStoreDir,
        return_internal_reference<>())
        ;

        // reduced functionality...
        // void SetPrimaryTransformer(G4PrimaryTransformer* pt)
        // void SetNumberOfAdditionalWaitingStacks(G4int iAdd)
        // void CutOffHasBeenModified()
        // void SetGeometryToBeOptimized(G4bool vl)
        // const G4Event* GetPreviousEvent(G4int i) const
        // void SetNumberOfEventsToBeStored(G4int val)
        // void SetDCtable(G4DCtable* DCtbl)
        */


            ;

}
