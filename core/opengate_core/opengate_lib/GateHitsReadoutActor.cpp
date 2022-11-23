/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#include "GateHitsReadoutActor.h"
#include "G4PhysicalVolumeStore.hh"
#include "GateHelpersDict.h"
#include "digitizer/GateDigiAdderInVolume.h"
#include "digitizer/GateDigiCollectionManager.h"
#include <iostream>

GateHitsReadoutActor::GateHitsReadoutActor(py::dict &user_info)
    : GateDigitizerAdderActor(user_info) {
  fDiscretizeVolumeDepth = -1;
}

GateHitsReadoutActor::~GateHitsReadoutActor() = default;

void GateHitsReadoutActor::SetDiscretizeVolumeDepth(int depth) {
  fDiscretizeVolumeDepth = depth;
}

void GateHitsReadoutActor::StartSimulationAction() {
  GateDigitizerAdderActor::StartSimulationAction();
  // Init a navigator that will be used to find the transform
  auto pvs = G4PhysicalVolumeStore::GetInstance();
  auto world = pvs->GetVolume("world");
  fNavigator = new G4Navigator();
  fNavigator->SetWorldVolume(world);
  // check param
  if (fDiscretizeVolumeDepth <= 0) {
    Fatal("Error in GateHitsReadoutActor, depth (fDiscretizeVolumeDepth) must "
          "be positive");
  }
}

void GateHitsReadoutActor::EndOfEventAction(const G4Event * /*unused*/) {
  // loop on all hits to group per volume ID
  auto &l = fThreadLocalData.Get();
  auto &iter = l.fInputIter;
  iter.GoToBegin();
  while (!iter.IsAtEnd()) {
    AddHitPerVolume();
    iter++;
  }

  // create the output hits collection for grouped hits
  for (auto &h : l.fMapOfHitsInVolume) {
    auto &hit = h.second;
    // terminate the merge
    hit.Terminate(fPolicy);
    // Don't store if edep is zero
    if (hit.fFinalEdep > 0) {
      // Discretize
      fNavigator->LocateGlobalPointAndUpdateTouchable(hit.fFinalPosition,
                                                      &fTouchableHistory);
      auto vid = GateUniqueVolumeID::New(&fTouchableHistory);
      auto tr = vid->GetLocalToWorldTransform(fDiscretizeVolumeDepth);
      G4ThreeVector c;
      tr->ApplyPointTransform(c);
      hit.fFinalPosition.set(c.getX(), c.getY(), c.getZ());

      // (all "Fill" calls are thread local)
      fOutputEdepAttribute->FillDValue(hit.fFinalEdep);
      fOutputPosAttribute->Fill3Value(hit.fFinalPosition);
      fOutputGlobalTimeAttribute->FillDValue(hit.fFinalTime);
      l.fHitsAttributeFiller->Fill(hit.fFinalIndex);
    }
  }

  // reset the structure of hits
  l.fMapOfHitsInVolume.clear();
}
