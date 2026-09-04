/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#include "GateFieldBase.h"
#include "GateHelpers.h"
#include <G4EventManager.hh>
#include <G4LogicalVolume.hh>
#include <G4NavigationHistory.hh>
#include <G4Navigator.hh>
#include <G4StateManager.hh>
#include <G4TouchableHistory.hh>
#include <G4Track.hh>
#include <G4TrackingManager.hh>
#include <G4TransportationManager.hh>
#include <G4VPhysicalVolume.hh>
#include <memory>
#include <sstream>
#include <stdexcept>

namespace {

// World-to-local transform of the deepest level of the history that places the
// given logical volume, or nullptr if the volume is not in the history at all.
const G4AffineTransform *findPlacement(const G4NavigationHistory *history,
                                       const G4LogicalVolume *lv) {
  if (history == nullptr)
    return nullptr;

  for (G4int n = static_cast<G4int>(history->GetDepth()); n >= 0; --n) {
    const G4VPhysicalVolume *pv = history->GetVolume(n);
    if (pv != nullptr && pv->GetLogicalVolume() == lv)
      return &history->GetTransform(n);
  }
  return nullptr;
}

// Navigation history of the track being tracked, or nullptr outside tracking.
const G4NavigationHistory *trackingHistory() {
  // G4TrackingManager::fpTrack is assigned in ProcessOneTrack and never
  // cleared, so GetTrack() keeps returning the last track after the event
  // manager has deleted it. Only trust it while an event is actually being
  // processed; outside that, the caller falls back to the navigator.
  if (G4StateManager::GetStateManager()->GetCurrentState() != G4State_EventProc)
    return nullptr;

  const G4EventManager *eventManager = G4EventManager::GetEventManager();
  const G4TrackingManager *trackingManager =
      (eventManager != nullptr) ? eventManager->GetTrackingManager() : nullptr;
  const G4Track *track =
      (trackingManager != nullptr) ? trackingManager->GetTrack() : nullptr;
  const G4VTouchable *touchable =
      (track != nullptr) ? track->GetTouchable() : nullptr;
  return (touchable != nullptr) ? touchable->GetHistory() : nullptr;
}

} // namespace

// constructor
GateFieldBase::GateFieldBase(const G4LogicalVolume *logicalVolume)
    : m_logicalVolume(logicalVolume) {
  if (logicalVolume == nullptr)
    throw std::invalid_argument(
        "GateFieldBase: logical volume must not be null");
}

// world-to-local transform of the placement of the field's logical volume that
// the current navigation history is in
G4AffineTransform GateFieldBase::findPlacementTransform() const {

  // During tracking, use the current track's navigation history.
  if (const G4AffineTransform *transform =
          findPlacement(trackingHistory(), m_logicalVolume))
    return *transform;

  // Outside tracking (e.g. when visualising with /vis/scene/add/magneticField),
  // use the navigator's history.
  const G4Navigator *navigator =
      G4TransportationManager::GetTransportationManager()
          ->GetNavigatorForTracking();
  if (navigator != nullptr) {
    const std::unique_ptr<G4TouchableHistory> touchable(
        navigator->CreateTouchableHistory());
    if (const G4AffineTransform *transform =
            findPlacement(touchable->GetHistory(), m_logicalVolume))
      return *transform;
  }

  // Neither source knows about the field's volume: there is no frame in which
  // the field is defined. This is a genuine inconsistency.
  std::ostringstream msg;
  msg << "GateFieldBase: the field's logical volume '"
      << m_logicalVolume->GetName()
      << "' does not appear in the current navigation history, so the local "
         "frame of the field is undefined.\n"
      << "  The field value was requested at a point that Geant4 does not "
         "locate inside (or below) that volume.\n"
      << "  This likely indicates a real bug in the geometry or field setup.\n";
  Fatal(msg.str());
  return G4AffineTransform(); // to avoid warning
}
