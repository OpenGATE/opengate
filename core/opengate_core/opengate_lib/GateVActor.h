/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#ifndef GateVActor_h
#define GateVActor_h

#include "GateVFilter.h"
#include <G4Event.hh>
#include <G4Run.hh>
#include <G4VPrimitiveScorer.hh>
#include <pybind11/stl.h>

namespace py = pybind11;

class GateSourceManager;

class GateVActor : public G4VPrimitiveScorer {

public:
  explicit GateVActor(py::dict &user_info, bool MT_ready = false);

  ~GateVActor() override;

  virtual void AddActions(std::set<std::string> &actions);

  // Called at initialisation
  virtual void InitializeCpp();

  // get user input parameters from python side
  virtual void InitializeUserInfo(py::dict &user_info);

  // Used to add a callback to a given volume.
  // Every step in this volume will trigger a SteppingAction
  void RegisterSD(G4LogicalVolume *lv);

  bool HasAction(const std::string &);

  bool IsSensitiveDetector();

  // Called when the simulation start (master thread only)
  virtual void StartSimulationAction() {}

  // Called when the simulation end (master thread only)
  virtual void EndSimulationAction() {}

  // Called by Geant4 every hit. Call SteppingAction and return True
  // Take care about the filters
  G4bool ProcessHits(G4Step *, G4TouchableHistory *) override;

  /*

   ************ WARNING ************

   * In multi-thread mode, there is (for the moment) a single actor object
   shared
   * by all threads. It means it is **required** to use mutex when modifying a
   * local variable. An alternative is to set all thread modifiable variables in
   * a thread_local structure with G4Cache<my_struct> (see for example in
   * G4SingleParticleSource). And merge at the end. (see
   * GateSimulationStatisticsActor). The second should be faster, but I did not
   * really test.
   *
   * Another alternative is to use G4VAccumulable (not fully clear how/when to
   * call Merge() however).
   *
   * Last alternative -> change python side to create one actor for each thread.
   * It takes more memory, but could be potentially faster (no lock).
   *
   * ... We left this as exercise for the reader ;)
   *
   */

  // Called by every worker when the simulation is about to end
  // (after last run)
  virtual void EndOfSimulationWorkerAction(const G4Run * /*lastRun*/) {}

  // Called every time a Run starts (all threads)
  virtual void BeginOfRunAction(const G4Run * /*run*/) {}

  // Called every time a Run starts (only the master thread)
  virtual void BeginOfRunActionMasterThread(int run_id) {}

  virtual int EndOfRunActionMasterThread(int run_id) { return 0; }

  // Called every time a Run ends (all threads)
  virtual void EndOfRunAction(const G4Run * /*run*/) {}

  // Called every time an Event starts (all threads)
  virtual void BeginOfEventAction(const G4Event * /*event*/) {}

  // Called every time an Event ends (all threads)
  virtual void EndOfEventAction(const G4Event * /*event*/) {}

  // Called every time a Track starts (even if not in the volume attached to
  // this actor)
  virtual void PreUserTrackingAction(const G4Track *track);

  // Called every time a Track ends
  virtual void PostUserTrackingAction(const G4Track *track);

  // Called every FillHits, should be overloaded
  virtual void SteppingAction(G4Step *) {}

  virtual void NewStage() {}

  void SetOutputPath(const std::string &outputName,
                     const std::string &outputPath);

  std::string GetOutputPath(std::string outputName) const;

  void SetWriteToDisk(const std::string &outputName, bool writeToDisk);

  bool GetWriteToDisk(std::string outputName) const;

  void AddActorOutputInfo(const std::string &outputName);

  bool IsStepExitVolume(const G4Step *step) const;

  inline static std::string fOutputNameRoot = "root_output";

  struct ActorOutputInfo {
    std::string outputName = "";
    std::string outputPath = "";
    bool writeToDisk = false;
  };

  typedef ActorOutputInfo ActorOutputInfo_t;

  std::map<std::string, ActorOutputInfo_t> fActorOutputInfos;

  void SetSourceManager(GateSourceManager *s);

  void SetMotherAttachedToVolumeName(const std::string &attachedToVolumeName);

  // List of actions (set to trigger some actions)
  // Can be set either on cpp or py side
  std::set<std::string> fActions;

  // Name of the mother volume (logical volume)
  std::string fAttachedToVolumeName;
  std::string fAttachedToVolumeMotherName;

  // List of active filters
  std::vector<GateVFilter *> fFilters;

  // Is this actor ok for multi-thread ?
  bool fMultiThreadReady;

  // Is the boolean operator between filters an 'and' ?
  bool fOperatorIsAnd;

  // Should this actor write to disk ?
  bool fWriteToDisk;

  GateSourceManager *fSourceManager;
};

#endif // GateVActor_h
