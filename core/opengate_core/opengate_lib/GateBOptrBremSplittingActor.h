//
// ********************************************************************
// * License and Disclaimer                                           *
// *                                                                  *
// * The  Geant4 software  is  copyright of the Copyright Holders  of *
// * the Geant4 Collaboration.  It is provided  under  the terms  and *
// * conditions of the Geant4 Software License,  included in the file *
// * LICENSE and available at  http://cern.ch/geant4/license .  These *
// * include a list of copyright holders.                             *
// *                                                                  *
// * Neither the authors of this software system, nor their employing *
// * institutes,nor the agencies providing financial support for this *
// * work  make  any representation or  warranty, express or implied, *
// * regarding  this  software system or assume any liability for its *
// * use.  Please see the license in the file  LICENSE  and URL above *
// * for the full disclaimer and the limitation of liability.         *
// *                                                                  *
// * This  code  implementation is the result of  the  scientific and *
// * technical work of the GEANT4 collaboration.                      *
// * By using,  copying,  modifying or  distributing the software (or *
// * any work based  on the software)  you  agree  to acknowledge its *
// * use  in  resulting  scientific  publications,  and indicate your *
// * acceptance of all terms of the Geant4 Software license.          *
// ********************************************************************
//
///
/// \file GateBOptrBremSplittingActor.h
/// \brief Definition of the GateBOptrBremSplittingActor class
#ifndef GateBOptrBremSplittingActor_h
#define GateBOptrBremSplittingActor_h 1

#include "G4VBiasingOperator.hh"

#include "GateVActor.h"
#include <iostream>
#include <pybind11/stl.h>
namespace py = pybind11;

class GateBOptnBremSplitting;

class GateBOptrBremSplittingActor : public G4VBiasingOperator,
                                    public GateVActor {
public:
  GateBOptrBremSplittingActor(py::dict &user_info);
  virtual ~GateBOptrBremSplittingActor() {}

public:
  // -------------------------
  // Optional from base class:
  // -------------------------
  // -- Call at run start:
  // virtual void BeginOfRunAction(const G4Run *run);

  // -- Call at each track starting:
  // virtual void PreUserTrackingAction( const G4Track* track );

  G4int fSplittingFactor;
  G4bool fBiasPrimaryOnly;
  G4bool fBiasOnlyOnce;
  G4int fNInteractions;
  // Unused but mandatory

  virtual void StartRun();
  virtual void StartTracking(const G4Track *);
  virtual void EndTracking() {}

protected:
  // -----------------------------
  // -- Mandatory from base class:
  // -----------------------------
  // -- Unused:

  virtual G4VBiasingOperation *ProposeNonPhysicsBiasingOperation(
      const G4Track * /* track */,
      const G4BiasingProcessInterface * /* callingProcess */) {
    return 0;
  }
  virtual G4VBiasingOperation *ProposeOccurenceBiasingOperation(
      const G4Track * /* track */,
      const G4BiasingProcessInterface * /* callingProcess */) {
    return 0;
  }

  // -- Used:
  virtual G4VBiasingOperation *ProposeFinalStateBiasingOperation(
      const G4Track *track, const G4BiasingProcessInterface *callingProcess);

private:
  // -- Avoid compiler complaining for (wrong) method shadowing,
  // -- this is because other virtual method with same name exists.
  using G4VBiasingOperator::OperationApplied;

private:
  GateBOptnBremSplitting *fBremSplittingOperation;
};

#endif
