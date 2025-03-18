/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#ifndef GateAcceptanceAngleTesterManager_h
#define GateAcceptanceAngleTesterManager_h

#include "G4AffineTransform.hh"
#include "GateAcceptanceAngleTester.h"
#include "GateHelpers.h"

class GateAcceptanceAngleTesterManager {
public:
  GateAcceptanceAngleTesterManager();

  enum AAPolicyType { AAZeroEnergy, AASkipEvent, AAUndefined };

  void Initialize(py::dict puser_info, bool is_iso);

  void InitializeAcceptanceAngle();

  unsigned long GetNumberOfNotAcceptedEvents() const;

  bool IsEnabled() const { return fEnabledFlag; }

  void StartAcceptLoop();

  bool TestIfAccept(const G4ThreeVector &position,
                    const G4ThreeVector &momentum_direction);

  AAPolicyType GetPolicy() const { return fPolicy; }

protected:
  AAPolicyType fPolicy;
  std::map<std::string, std::string> fAcceptanceAngleParam;
  std::vector<GateAcceptanceAngleTester *> fAATesters{};
  std::vector<std::string> fAcceptanceAngleVolumeNames;
  bool fEnabledFlag;
  unsigned long fNotAcceptedEvents;
  unsigned long fMaxNotAcceptedEvents;
  int fAALastRunId;
};

#endif // GateAcceptanceAngleTesterManager_h
