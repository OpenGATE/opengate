/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#ifndef GateGenericSource_h
#define GateGenericSource_h

#include "GateSingleParticleSource.h"
#include "GateVSource.h"
#include <pybind11/stl.h>

namespace py = pybind11;

class GateGenericSource : public GateVSource {

public:
  GateGenericSource();

  virtual ~GateGenericSource();

  virtual void CleanWorkerThread();

  virtual void InitializeUserInfo(py::dict &user_info);

  virtual double PrepareNextTime(double current_simulation_time);

  virtual void PrepareNextRun();

  virtual void GeneratePrimaries(G4Event *event, double time);

  /// Current number of simulated event in this source
  int fNumberOfGeneratedEvents;

  /// if acceptance angle, this variable store the total number of trials
  unsigned long fAASkippedParticles;

  void SetEnergyCDF(std::vector<double> cdf) { fEnergyCDF = cdf; }

  void SetProbabilityCDF(std::vector<double> cdf) { fProbabilityCDF = cdf; }

protected:
  int fMaxN;
  // We cannot not use a std::unique_ptr
  // (or maybe by controlling the deletion during the CleanWorkerThread ?)
  GateSingleParticleSource *fSPS;

  double fActivity;
  double fInitialActivity;
  double fHalfLife;
  double fLambda;
  G4ParticleDefinition *fParticleDefinition;

  // generic ion is controlled separately (maybe initialized once Run is
  // started)
  bool fIsGenericIon;
  int fA;    // A: Atomic Mass (nn + np +nlambda)
  int fZ;    // Z: Atomic Number
  double fE; // E: Excitation energy
  double fWeight;
  double fWeightSigma;

  // if confine is used, must be defined after the initialization
  bool fInitConfine;
  std::string fConfineVolume;

  // for beta plus CDF
  std::vector<double> fEnergyCDF;
  std::vector<double> fProbabilityCDF;

  virtual void InitializeParticle(py::dict &user_info);

  virtual void InitializeIon(py::dict &user_info);

  virtual void InitializeHalfTime(G4ParticleDefinition *p);

  virtual void InitializePosition(py::dict user_info);

  virtual void InitializeDirection(py::dict user_info);

  virtual void InitializeEnergy(py::dict user_info);

  virtual void UpdateActivity(double time);
};

#endif // GateGenericSource_h
