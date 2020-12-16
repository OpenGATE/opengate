/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */
#include <pybind11/pybind11.h>

#include "G4RunManager.hh"
#include "G4VUserDetectorConstruction.hh"
#include "G4VUserPrimaryGeneratorAction.hh"
#include "G4VUserPhysicsList.hh"
#include "G4VUserActionInitialization.hh"

namespace py = pybind11;

void init_G4RunManager(py::module &m) {

    // No destructor for this singleton class because seg fault from py side
    py::class_<G4RunManager, std::unique_ptr<G4RunManager, py::nodelete>>(m, "G4RunManager")
            .def(py::init())
            .def_static("GetRunManager", &G4RunManager::GetRunManager, py::return_value_policy::reference)
            .def("Initialize", &G4RunManager::Initialize)
            .def("RestoreRandomNumberStatus", &G4RunManager::RestoreRandomNumberStatus)

            .def("SetUserInitialization",
                 py::overload_cast<G4VUserDetectorConstruction *>(&G4RunManager::SetUserInitialization))
            .def("SetUserInitialization",
                 py::overload_cast<G4VUserPhysicsList *>(&G4RunManager::SetUserInitialization))
            .def("SetUserInitialization",
                 py::overload_cast<G4VUserActionInitialization *>(&G4RunManager::SetUserInitialization))
            .def("SetUserAction",
                 py::overload_cast<G4VUserPrimaryGeneratorAction *>(&G4RunManager::SetUserAction))

            .def("SetVerboseLevel", &G4RunManager::SetVerboseLevel)
            .def("GetVerboseLevel", &G4RunManager::GetVerboseLevel)
            .def("Initialize", &G4RunManager::Initialize)

                    //.def("BeamOn", &G4RunManager::BeamOn)
            .def("BeamOn", [](G4RunManager *mt, G4int n_event, const char *macroFile, G4int n_select) {
                std::cout << "GAM_G4 G4RunManager::BeamOn" << std::endl;
                py::gil_scoped_release release;
                std::cout << "after gil_scoped_release" << std::endl;
                mt->BeamOn(n_event, macroFile, n_select);
                std::cout << "END GAM_G4 G4RunManager::BeamOn" << std::endl;
            })


            .def("AbortRun", &G4RunManager::AbortRun)
            .def("ConfirmBeamOnCondition", &G4RunManager::ConfirmBeamOnCondition)
            .def("RunTermination", &G4RunManager::RunTermination)
            .def("TerminateEventLoop", &G4RunManager::TerminateEventLoop)
            .def("RunInitialization", &G4RunManager::RunInitialization)
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
        &G4RunManager::GetUserDetectorConstruction,
        return_internal_reference<>())
        .def("GetUserPhysicsList",
        &G4RunManager::GetUserPhysicsList,
        return_internal_reference<>())
        .def("GetUserPrimaryGeneratorAction",
        &G4RunManager::GetUserPrimaryGeneratorAction,
        return_internal_reference<>())
        .def("GetUserRunAction",      &G4RunManager::GetUserRunAction,
        return_internal_reference<>())
        .def("GetUserEventAction",    &G4RunManager::GetUserEventAction,
        return_internal_reference<>())
        .def("GetUserStackingAction", &G4RunManager::GetUserStackingAction,
        return_internal_reference<>())
        .def("GetUserTrackingAction", &G4RunManager::GetUserTrackingAction,
        return_internal_reference<>())
        .def("GetUserSteppingAction", &G4RunManager::GetUserSteppingAction,
        return_internal_reference<>())
        // ---
        .def("AbortRun",             &G4RunManager::AbortRun,
        f_AbortRun((arg("soft_abort")=false),
        "Abort run (event loop)."))
        .def("AbortEvent",           &G4RunManager::AbortEvent)
        .def("DefineWorldVolume",    &G4RunManager::DefineWorldVolume,
        f_DefineWorldVolume())
        .def("DumpRegion",           f1_DumpRegion)
        .def("DumpRegion",           f2_DumpRegion, f_DumpRegion())
        .def("rndmSaveThisRun",      &G4RunManager::rndmSaveThisRun)
        .def("rndmSaveThisEvent",    &G4RunManager::rndmSaveThisEvent)
        .def("RestoreRandomNumberStatus",
        &G4RunManager::RestoreRandomNumberStatus)
        .def("SetRandomNumberStore", &G4RunManager::SetRandomNumberStore)
        .def("GetRandomNumberStore", &G4RunManager::GetRandomNumberStore)
        .def("SetRandomNumberStoreDir", &G4RunManager::SetRandomNumberStoreDir)
        .def("GeometryHasBeenModified", &G4RunManager::GeometryHasBeenModified,
        f_GeometryHasBeenModified())
        .def("PhysicsHasBeenModified",  &G4RunManager::PhysicsHasBeenModified)
        .def("GetGeometryToBeOptimized",&G4RunManager::GetGeometryToBeOptimized)
        .def("GetCurrentRun",  &G4RunManager::GetCurrentRun,
        return_value_policy<reference_existing_object>())
        .def("GetCurrentEvent", &G4RunManager::GetCurrentEvent,
        return_value_policy<reference_existing_object>())
        .def("SetRunIDCounter",        &G4RunManager::SetRunIDCounter)
        .def("GetVersionString",     &G4RunManager::GetVersionString,
        return_value_policy<reference_existing_object>())
        .def("GetRandomNumberStoreDir", &G4RunManager::GetRandomNumberStoreDir,
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
