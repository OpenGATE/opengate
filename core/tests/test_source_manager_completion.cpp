// Real sequential Geant4 event loop with replay work published by EndOfEvent.
#include "GateSourceManager.h"
#include "GateEventAction.h"
#include "GateRunAction.h"
#include <G4Box.hh>
#include <G4Geantino.hh>
#include <G4LogicalVolume.hh>
#include <G4NistManager.hh>
#include <G4PVPlacement.hh>
#include <G4RunManager.hh>
#include <G4VUserDetectorConstruction.hh>
#include <G4VUserPhysicsList.hh>
#include <pybind11/embed.h>
#undef NDEBUG
#include <cassert>
#include <iostream>

struct World : G4VUserDetectorConstruction {
  G4VPhysicalVolume *Construct() override {
    auto *lv = new G4LogicalVolume(new G4Box("world", 10, 10, 10),
        G4NistManager::Instance()->FindOrBuildMaterial("G4_Galactic"), "world");
    return new G4PVPlacement(nullptr, {}, lv, "world", nullptr, false, 0);
  }
};
struct Physics : G4VUserPhysicsList {
  void ConstructParticle() override { G4Geantino::GeantinoDefinition(); }
  void ConstructProcess() override { AddTransportation(); }
  void SetCuts() override { SetCutsWithDefault(); }
};
struct Source : GateVSource {
  int quota = 0, generated = 0, total = 0, selections = 0, cleaned = 0;
  bool replay;
  Source(const char *name, bool r) : replay(r) { fName = name; }
  void PrepareNextRun() override { generated = 0; if (replay) quota = 0; }
  double PrepareNextTime(double current, unsigned long) override {
    ++selections;
    return generated < quota ? current + (replay ? 0.2 : 0.1) : -1;
  }
  bool HasPendingEvents() const override { return replay && generated < quota; }
  void CleanWorkerThread() override { ++cleaned; }
  void GeneratePrimaries(G4Event *event, double time) override {
    ++generated; ++total;
    auto *v = new G4PrimaryVertex({}, time);
    auto *p = new G4PrimaryParticle(G4Geantino::GeantinoDefinition());
    p->SetMomentumDirection({0,0,1}); p->SetKineticEnergy(1);
    v->SetPrimary(p); event->AddPrimaryVertex(v);
  }
};
struct Producer : GateVActor {
  GateSourceManager *manager;
  Source *original, *replay;
  bool deferred, publish, stop;
  int events = 0, finalizations = 0, runs = 0;
  Producer(py::dict &info, GateSourceManager *m, Source *o, Source *r,
           bool d, bool p, bool s) : GateVActor(info), manager(m), original(o),
           replay(r), deferred(d), publish(p), stop(s) {
    fActions = {"BeginOfRunAction", "EndOfEventAction", "EndOfSimulationWorkerAction"};
  }
  void BeginOfRunAction(const G4Run *) override {
    ++runs; if (deferred) manager->DeferRunCompletion();
  }
  void EndOfEventAction(const G4Event *) override {
    ++events;
    if (manager->GetGeneratingSourceName() == "original" && publish) {
      replay->quota = 2; replay->generated = 0;
      manager->SetActiveSourcebyName("replay");
    } else if (replay->HasPendingEvents()) {
      manager->SetActiveSourcebyName("replay");
    }
    if (stop) GateSourceManager::SetRunTerminationFlag(true);
  }
  void EndOfSimulationWorkerAction(const G4Run *) override { ++finalizations; }
};
int main(int argc, char **argv) {
  py::scoped_interpreter python;
  const std::string mode = argc > 1 ? argv[1] : "replays";
  const bool deferred = mode != "ordinary";
  const bool publish = mode == "replays" || mode == "stop" || mode == "limit";
  auto *run = new G4RunManager;
  run->SetVerboseLevel(0);
  run->SetUserInitialization(new World);
  run->SetUserInitialization(new Physics);
  auto *manager = new GateSourceManager;
  Source original("original", false), replay("replay", true);
  original.quota = mode == "empty" ? 0 : 1;
  manager->AddSource(&original); manager->AddSource(&replay);
  manager->fSimulationTimes = {{0,1}, {1,2}};
  GateSourceManager::SetMaxPrimariesPerRun(mode == "limit" ? 1 : 100);
  py::dict info; info["name"] = "producer";
  Producer actor(info, manager, &original, &replay, deferred, publish, mode == "stop");
  manager->SetActors({&actor});
  run->SetUserAction(manager);
  auto *ra = new GateRunAction(manager); ra->RegisterActor(&actor);
  run->SetUserAction(ra);
  auto *ea = new GateEventAction; ea->RegisterActor(&actor);
  run->SetUserAction(ea);
  run->Initialize();
  try {
    manager->StartMasterThread();
  } catch (const std::runtime_error &error) {
    assert(mode == "stop" || mode == "limit");
    assert(std::string(error.what()).find("history incomplete") != std::string::npos);
    assert(replay.HasPendingEvents());
    assert(actor.finalizations == 0);
    std::cout << "PASS explicit incomplete-history failure: " << mode << std::endl;
    // Geant4 did not complete its run normally; leave teardown to process exit.
    return 0;
  }
  assert(mode != "stop" && mode != "limit"); // these must fail with pending work
  assert(actor.runs == 2 && actor.finalizations == 1);
  assert(manager->GetCurrentRunId() == 2);
  assert(original.cleaned == 1 && replay.cleaned == 1);
  assert(original.total == (mode == "empty" ? 0 : 2));
  assert(replay.total == (publish ? 4 : 0));
  assert(actor.events == (publish ? 6 : 2));
  assert(original.selections == 2 + actor.events);
  assert(replay.selections == original.selections);
  assert(!replay.HasPendingEvents());
  // Duplicate completion must not advance the run a second time.
  manager->CheckForNextRun();
  assert(manager->GetCurrentRunId() == 2);
  delete run;
  std::cout << "PASS completion: " << mode << std::endl;
}
