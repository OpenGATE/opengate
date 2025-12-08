/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#include "GateDigitizerReadoutActor.h"
#include "../GateHelpers.h"
#include "../GateHelpersDict.h"
#include "G4Navigator.hh"
#include "G4PhysicalVolumeStore.hh"
#include "GateDigiAdderInVolume.h"
#include "GateDigiCollectionManager.h"
#include <iostream>

G4Mutex SetIgnoredHitsMutex = G4MUTEX_INITIALIZER;

GateDigitizerReadoutActor::GateDigitizerReadoutActor(py::dict &user_info)
    : GateDigitizerAdderActor(user_info) {
  fDiscretizeVolumeDepth = -1;
  fIgnoredHitsCount = 0;
}

GateDigitizerReadoutActor::~GateDigitizerReadoutActor() = default;

void GateDigitizerReadoutActor::SetDiscretizeVolumeDepth(const int depth) {
  fDiscretizeVolumeDepth = depth;
}

void GateDigitizerReadoutActor::StartSimulationAction() {
  GateDigitizerAdderActor::StartSimulationAction();
  fIgnoredHitsCount = 0;
  // check param
  if (fDiscretizeVolumeDepth <= 0) {
    Fatal("Error in GateDigitizerReadoutActor, depth (fDiscretizeVolumeDepth) "
          "must be positive");
  }
}

void GateDigitizerReadoutActor::BeginOfRunAction(const G4Run *run) {
  GateDigitizerAdderActor::BeginOfRunAction(run);
  if (run->GetRunID() == 0) {
    // Init a navigator that will be used to find the transform
    auto pvs = G4PhysicalVolumeStore::GetInstance();
    auto world = pvs->GetVolume("world");
    auto &lr = fThreadLocalReadoutData.Get();
    lr.fNavigator = new G4Navigator();
    lr.fNavigator->SetWorldVolume(world);
    lr.fIgnoredHitsCount = 0;
  } else {
    auto &lr = fThreadLocalReadoutData.Get();
    lr.fNavigator->ResetStackAndState();
  }
}

void GateDigitizerReadoutActor::EndOfEventAction(const G4Event * /*unused*/) {
  // get thread local data
  auto &l = fThreadLocalData.Get();
  auto &lr = fThreadLocalVDigitizerData.Get();
  auto &lro = fThreadLocalReadoutData.Get();
  // loop on all digi to group per volume ID
  auto &iter = lr.fInputIter;
  iter.GoToBegin();
  while (!iter.IsAtEnd()) {
    AddDigiPerVolume();
    iter++;
  }

  // create the output digi collection for grouped digi
  for (auto &h : l.fMapOfDigiInVolume) {
    const auto &digi = h.second;
    // terminate the merge
    digi->Terminate();

    // Only store if edep is not zero
    if (digi->fFinalEdep > 0) {
      // Discretize: find the volume that contains the position
      G4TouchableHistory fTouchableHistory;
      lro.fNavigator->LocateGlobalPointAndUpdateTouchable(digi->fFinalPosition,
                                                          &fTouchableHistory);

      /*
       FIXME:  When computing the centroid, the final position maybe outside the
       DiscretizeVolume. In that case, should we ignore the hits?
       */

      // Compute the position of the center of the volume (0,0,0) in the world
      // coordinate system
      G4ThreeVector c;
      c = fTouchableHistory.GetHistory()
              ->GetTransform(fDiscretizeVolumeDepth)
              .InverseTransformPoint(c);
      digi->fFinalPosition.set(c.getX(), c.getY(), c.getZ());

      // (all "Fill" calls are thread local)
      fOutputEdepAttribute->FillDValue(digi->fFinalEdep);
      fOutputPosAttribute->Fill3Value(digi->fFinalPosition);
      fOutputGlobalTimeAttribute->FillDValue(digi->fFinalTime);
      lr.fDigiAttributeFiller->Fill(digi->fFinalIndex);
    }
  }

  // reset the structure of digi
  l.fMapOfDigiInVolume.clear();
}

void GateDigitizerReadoutActor::EndOfSimulationWorkerAction(
    const G4Run * /*lastRun*/) {
  auto &lr = fThreadLocalReadoutData.Get();
  G4AutoLock mutex(&SetIgnoredHitsMutex);
  fIgnoredHitsCount += lr.fIgnoredHitsCount;
  fOutputDigiCollection->Write();
}
