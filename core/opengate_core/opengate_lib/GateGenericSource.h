/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#ifndef GateGenericSource_h
#define GateGenericSource_h

#include "GateAcceptanceAngleManager.h"
#include "GateSingleParticleSource.h"
#include "GateVSource.h"
#include "biasing/GateForcedDirectionManager.h"
#include <pybind11/stl.h>

namespace py = pybind11;

class GateGenericSource : public GateVSource {

public:
  GateGenericSource();

  ~GateGenericSource() override;

  void CleanWorkerThread() override;

  void InitializeUserInfo(py::dict &user_info) override;

  double PrepareNextTime(double current_simulation_time,
                         double NumberOfGeneratedEvents) override;

  void PrepareNextRun() override;

  void GeneratePrimaries(G4Event *event,
                         double current_simulation_time) override;

  void SetEnergyCDF(const std::vector<double> &cdf);

  void SetProbabilityCDF(const std::vector<double> &cdf);

  void SetTAC(const std::vector<double> &times,
              const std::vector<double> &activities);

  void InitializeBackToBackMode(py::dict &user_info);

  unsigned long GetTotalSkippedEvents() const;
  unsigned long GetTotalZeroEvents() const;

protected:
  //  We cannot use a std::unique_ptr
  //  (or maybe by controlling the deletion during the CleanWorkerThread ?)
  G4ParticleDefinition *fParticleDefinition;
  G4ThreeVector fInitializeMomentum;
  G4ThreeVector fInitializeFocusPoint;
  G4ThreeVector fInitTranslation;
  G4String fangType;
  double fUserParticleLifeTime;

  // Time Curve Activity
  std::vector<double> fTAC_Times;
  std::vector<double> fTAC_Activities;
  void UpdateActivityWithTAC(double time);

  // generic ion is controlled separately
  // (maybe initialized once Run is started)
  // bool fInitGenericIon;
  int fA;    // A: Atomic Mass (nn + np +nlambda)
  int fZ;    // Z: Atomic Number
  double fE; // E: Excitation energy
  double fWeight;
  double fWeightSigma;

  // back to back source
  bool fBackToBackMode;

  // Force the rotation of momentum and focal point to follow rotation of the
  // source, eg: needed for motion actor
  bool fDirectionRelativeToAttachedVolume;

  // thread local structure
  struct threadLocalGenericSource {
    GateSingleParticleSource *fSPS = nullptr;
    GateAcceptanceAngleManager *fAAManager = nullptr;
    GateForcedDirectionManager *fFDManager = nullptr;
    bool fInitConfine = false;
    bool fInitGenericIon = false;
    double fEffectiveEventTime = -1;
    unsigned long fCurrentSkippedEvents = 0;
    unsigned long fCurrentZeroEvents = 0;
  };
  G4Cache<threadLocalGenericSource> fThreadLocalDataGenericSource;

  // sum of all threads
  unsigned long fTotalSkippedEvents = 0;
  unsigned long fTotalZeroEvents = 0;

  threadLocalGenericSource &GetThreadLocalDataGenericSource() const;

  // if confine is used, must be defined after the initialization
  // bool fInitConfine;
  std::string fConfineVolume;

  // for beta plus CDF
  std::vector<double> fEnergyCDF;
  std::vector<double> fProbabilityCDF;

  virtual void InitializeParticle(py::dict &user_info);

  virtual void CreateSPS();

  virtual void InitializeIon(py::dict &user_info);

  virtual void SetLifeTime(G4ParticleDefinition *p);

  virtual void InitializePosition(py::dict user_info);

  virtual void InitializeDirection(py::dict user_info);

  virtual void InitializePolarization(py::dict user_info);

  virtual void InitializeEnergy(py::dict user_info);

  void UpdateActivity(double time) override;

  void UpdateEffectiveEventTime(double current_simulation_time,
                                unsigned long skipped_particle) const;
};

#endif // GateGenericSource_h
