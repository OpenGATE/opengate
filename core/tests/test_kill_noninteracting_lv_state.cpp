// Exercise real selection callbacks concurrently, with controlled Geant4 steps.
#include "GateKillNonInteractingParticleForLVActor.h"
#include <G4Box.hh>
#include <G4Geantino.hh>
#include <G4GeometryWorkspace.hh>
#include <G4LogicalVolume.hh>
#include <G4NavigationHistory.hh>
#include <G4PVPlacement.hh>
#include <G4ParticleTable.hh>
#include <G4TouchableHistory.hh>
#include <pybind11/embed.h>
#include <atomic>
#include <cstdlib>
#include <iostream>
#include <thread>

void require(bool value, const char *message) {
  if (!value) { std::cerr << message << std::endl; std::abort(); }
}
G4TouchableHandle touchable(G4VPhysicalVolume *volume) {
  G4NavigationHistory history;
  if (volume) history.SetFirstEntry(volume);
  return G4TouchableHandle(new G4TouchableHistory(history));
}
void step(GateKillNonInteractingParticleForLVActor &actor, G4Track &track,
          G4VPhysicalVolume *pre, G4VPhysicalVolume *post,
          double preEnergy, double postEnergy,
          G4StepStatus status = fGeomBoundary) {
  G4Step s;
  s.SetTrack(&track);
  s.GetPreStepPoint()->SetTouchableHandle(touchable(pre));
  s.GetPostStepPoint()->SetTouchableHandle(touchable(post));
  s.GetPreStepPoint()->SetStepStatus(fGeomBoundary);
  s.GetPostStepPoint()->SetStepStatus(status);
  s.GetPreStepPoint()->SetKineticEnergy(preEnergy);
  s.GetPostStepPoint()->SetKineticEnergy(postEnergy);
  actor.SteppingAction(&s);
}
int main() {
  py::scoped_interpreter python;
  auto *particle = G4Geantino::GeantinoDefinition();
  auto *worldLV = new G4LogicalVolume(new G4Box("world", 10,10,10), nullptr, "world");
  auto *boxLV = new G4LogicalVolume(new G4Box("box", 1,1,1), nullptr, "box");
  auto *world = new G4PVPlacement(nullptr, {}, worldLV, "world", nullptr, false, 0);
  auto *box = new G4PVPlacement(nullptr, {}, boxLV, "box", worldLV, false, 0);
  for (int workers : {1,2,4,8}) {
    py::dict info; info["name"] = "kill_lv"; info["attached_to"] = "box";
    GateKillNonInteractingParticleForLVActor actor(info), other(info);
    actor.InitializeUserInfo(info);
    actor.fListOfVolumeAncestor = {"world"};
    actor.StartSimulationAction(); other.StartSimulationAction();
    std::atomic<int> ready{0}; std::vector<std::thread> threads;
    for (int worker=0; worker<workers; ++worker) threads.emplace_back([&,worker] {
      // Real Geant4 workers copy geometry split data before using touchables.
      G4GeometryWorkspace geometry;
      auto &state = actor.fWorkerState.Get();
      require(&state != &other.fWorkerState.Get(), "Actors share worker state");
      G4Track track(new G4DynamicParticle(particle, {0,0,1}, 10), 0, {});
      track.SetLogicalVolumeAtVertex(worldLV); track.SetTrackID(worker+1);
      actor.PreUserTrackingAction(&track);
      step(actor, track, box, box, 10+worker, 10+worker);
      ++ready; while (ready.load()!=workers) std::this_thread::yield();
      require(state.fKineticEnergyAtTheEntrance == 10+worker, "Shared entry energy");
      require(state.fTrackIDAtTheEntrance == worker+1, "Shared track identity");
      step(actor, track, box, world, 10+worker, 10+worker);
      require(track.GetTrackStatus()==fStopAndKill, "Equal-energy exit survived");
      require(state.fNbOfKilledParticles==1, "Lost local count");
      // A changed exit energy survives, even after another track was killed.
      track.SetTrackStatus(fAlive); actor.PreUserTrackingAction(&track);
      step(actor, track, box, box, 10,10);
      step(actor, track, box, world, 10,9);
      require(track.GetTrackStatus()==fAlive, "Energy-changing track was killed");
      // Tracks born inside retain the historical exemption.
      track.SetLogicalVolumeAtVertex(boxLV); actor.PreUserTrackingAction(&track);
      step(actor, track, box, world, 10,10);
      require(track.GetTrackStatus()==fAlive, "In-volume birth rule changed");
      // Null post volume at a world exit must be safe even with saved entry.
      track.SetLogicalVolumeAtVertex(worldLV); actor.PreUserTrackingAction(&track);
      step(actor, track, box, box, 10,10);
      step(actor, track, box, nullptr, 10,10, fWorldBoundary);
      require(track.GetTrackStatus()==fAlive, "World exit changed selection");
      actor.EndOfSimulationWorkerAction(nullptr);
      actor.EndOfSimulationWorkerAction(nullptr);
      geometry.DestroyWorkspace();
    });
    for (auto &thread:threads) thread.join();
    require(actor.GetNumberOfKilledParticles()==workers, "Wrong reduced count");
    require(other.GetNumberOfKilledParticles()==0, "Actor reductions interfere");
    actor.StartSimulationAction();
    require(actor.GetNumberOfKilledParticles()==0, "Total did not reset");
    std::cout << "PASS kill LV state/selection: " << workers << " workers\n";
  }
}
