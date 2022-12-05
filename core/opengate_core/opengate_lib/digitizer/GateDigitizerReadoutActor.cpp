/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#include "GateDigitizerReadoutActor.h"
#include "../GateHelpersDict.h"
#include "G4PhysicalVolumeStore.hh"
#include "GateDigiAdderInVolume.h"
#include "GateDigiCollectionManager.h"
#include <iostream>

GateDigitizerReadoutActor::GateDigitizerReadoutActor(py::dict &user_info)
    : GateDigitizerAdderActor(user_info) {
  fDiscretizeVolumeDepth = -1;
}

GateDigitizerReadoutActor::~GateDigitizerReadoutActor() = default;

void GateDigitizerReadoutActor::SetDiscretizeVolumeDepth(int depth) {
  fDiscretizeVolumeDepth = depth;
}

void GateDigitizerReadoutActor::StartSimulationAction() {
  GateDigitizerAdderActor::StartSimulationAction();
  // Init a navigator that will be used to find the transform
  auto pvs = G4PhysicalVolumeStore::GetInstance();
  auto world = pvs->GetVolume("world");
  fNavigator = new G4Navigator();
  fNavigator->SetWorldVolume(world);
  DDD(fNavigator); // FIXME MT ??
  fIgnoredHitsCount = 0;
  // check param
  if (fDiscretizeVolumeDepth <= 0) {
    Fatal("Error in GateDigitizerReadoutActor, depth (fDiscretizeVolumeDepth) "
          "must "
          "be positive");
  }
}

void GateDigitizerReadoutActor::EndOfEventAction(const G4Event * /*unused*/) {
  // loop on all digi to group per volume ID
  auto &l = fThreadLocalData.Get();
  auto &iter = l.fInputIter;
  iter.GoToBegin();
  while (!iter.IsAtEnd()) {
    AddDigiPerVolume();
    iter++;
  }

  // create the output digi collection for grouped digi
  for (auto &h : l.fMapOfDigiInVolume) {
    auto &digi = h.second;
    // terminate the merge
    digi.Terminate(fPolicy);
    // Don't store if edep is zero
    if (digi.fFinalEdep > 0) {
      // Discretize: find the volume that contains the position
      G4TouchableHistory fTouchableHistory;
      fNavigator->LocateGlobalPointAndUpdateTouchable(digi.fFinalPosition,
                                                      &fTouchableHistory);
      auto vid = GateUniqueVolumeID::New(&fTouchableHistory);

      /* When computing the centroid, the final position maybe outside the
       * DiscretizeVolume. In that case, we ignore the hits */
      if (fDiscretizeVolumeDepth >= vid->GetDepth()) {
        fIgnoredHitsCount++;
        continue;
      }
      auto tr = vid->GetLocalToWorldTransform(fDiscretizeVolumeDepth);
      G4ThreeVector c;
      tr->ApplyPointTransform(c);

      if (isnan(c.getX()) or isnan(c.getY()) or isnan(c.getZ()) or
          c.getX() > 10000 or c.getY() > 10000 or c.getZ() > 10000) {
        DDD(c);
        DDD(fDiscretizeVolumeDepth);
        DDD(l.fMapOfDigiInVolume.size());
        DDD(digi.fFinalEdep);
        DDD(digi.fFinalPosition);
        DDD(fTouchableHistory.GetVolume()->GetName());
        DDD(fTouchableHistory.GetHistoryDepth());
        DDD(fTouchableHistory.GetCopyNumber());
        DDD(vid.get()->fID);
        DDD(tr->NetTranslation());
        DDD(tr->NetRotation());

        auto vid2 = GateUniqueVolumeID::New(&fTouchableHistory, true);
        auto tr2 = vid->GetLocalToWorldTransform(fDiscretizeVolumeDepth);
        DDD(tr2->NetTranslation());
      }

      digi.fFinalPosition.set(c.getX(), c.getY(), c.getZ());

      // (all "Fill" calls are thread local)
      fOutputEdepAttribute->FillDValue(digi.fFinalEdep);
      fOutputPosAttribute->Fill3Value(digi.fFinalPosition);
      fOutputGlobalTimeAttribute->FillDValue(digi.fFinalTime);
      l.fDigiAttributeFiller->Fill(digi.fFinalIndex);
    }
  }

  // reset the structure of digi
  l.fMapOfDigiInVolume.clear();
}
