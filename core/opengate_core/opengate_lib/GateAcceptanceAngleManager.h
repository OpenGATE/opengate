/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#ifndef GateAcceptanceAngleManager_h
#define GateAcceptanceAngleManager_h

#include "GateAcceptanceAngleSingleVolume.h"
#include "GateHelpers.h"

class GateAcceptanceAngleManager {
public:
  GateAcceptanceAngleManager();

  ~GateAcceptanceAngleManager();

  enum AAPolicyType { AAZeroEnergy, AASkipEvent, AAUndefined };

  void Initialize(const std::map<std::string, std::string> &user_info,
                  bool is_valid_type);

  void InitializeAcceptanceAngle();

  unsigned long GetNumberOfNotAcceptedEvents() const;

  bool IsEnabled() const { return fEnabledFlag; }

  void StartAcceptLoop();

  bool TestIfAccept(const G4ThreeVector &position,
                    const G4ThreeVector &momentum_direction);

  void PrepareCheck(const G4ThreeVector &position) const;
  bool TestDirection(const G4ThreeVector &momentum_direction) const;

  AAPolicyType GetPolicy() const { return fPolicy; }

  AAPolicyType fPolicy;
  std::map<std::string, std::string> fAcceptanceAngleParam;
  std::vector<GateAcceptanceAngleSingleVolume *> fAATesters{};
  std::vector<std::string> fAcceptanceAngleVolumeNames;
  bool fEnabledFlag;
  unsigned long fNotAcceptedEvents;
  unsigned long fMaxNotAcceptedEvents;
  int fAALastRunId;
};

#endif // GateAcceptanceAngleManager_h
