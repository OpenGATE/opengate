// Controlled selection callbacks and final count reduction on native threads.
#include "GateKillAccordingParticleNameLVActor.h"
#include <G4Box.hh>
#include <G4ChargedGeantino.hh>
#include <G4Geantino.hh>
#include <G4GeometryWorkspace.hh>
#include <G4LogicalVolume.hh>
#include <G4NavigationHistory.hh>
#include <G4PVPlacement.hh>
#include <G4TouchableHistory.hh>
#include <pybind11/embed.h>
#include <atomic>
#include <cstdlib>
#include <iostream>
#include <thread>

void require(bool value, const char *message) {
  if (!value) { std::cerr << message << std::endl; std::abort(); }
}
void step(GateKillAccordingParticleNameLVActor &actor, G4Track &track,
          G4VPhysicalVolume *destination, G4StepStatus status=fGeomBoundary) {
  G4NavigationHistory history;
  if (destination) history.SetFirstEntry(destination);
  G4Step s;
  s.SetTrack(&track);
  s.GetPostStepPoint()->SetStepStatus(status);
  s.GetPostStepPoint()->SetTouchableHandle(
      G4TouchableHandle(new G4TouchableHistory(history)));
  actor.SteppingAction(&s);
}
int main() {
  py::scoped_interpreter python;
  G4ParticleDefinition *selected = G4Geantino::GeantinoDefinition();
  G4ParticleDefinition *unselected = G4ChargedGeantino::ChargedGeantinoDefinition();
  auto *worldLV = new G4LogicalVolume(new G4Box("world",10,10,10),nullptr,"world");
  auto *boxLV = new G4LogicalVolume(new G4Box("box",1,1,1),nullptr,"box");
  auto *world = new G4PVPlacement(nullptr,{},worldLV,"world",nullptr,false,0);
  auto *box = new G4PVPlacement(nullptr,{},boxLV,"box",worldLV,false,0);
  for (int workers : {1,2,4,8}) {
    py::dict info; info["name"]="kill_name_lv"; info["attached_to"]="box";
    info["particles_name_to_kill"]=std::vector<std::string>{"geantino"};
    GateKillAccordingParticleNameLVActor actor(info), other(info);
    actor.InitializeUserInfo(info); actor.fListOfVolumeAncestor={"world"};
    actor.StartSimulationAction(); other.StartSimulationAction();
    std::atomic<int> ready{0}; std::vector<std::thread> threads;
    for (int worker=0; worker<workers; ++worker) threads.emplace_back([&,worker] {
      G4GeometryWorkspace geometry;
      auto &state=actor.fThreadLocalData.Get();
      require(&state!=&other.fThreadLocalData.Get(),"Actors share state");
      for (int iteration=0; iteration<2; ++iteration) {
        const bool wanted=(worker+iteration)%2==0;
        G4Track track(new G4DynamicParticle(wanted?selected:unselected,{0,0,1},1),0,{});
        actor.PreUserTrackingAction(&track);
        if (iteration==0) {
          ++ready; while (ready.load()!=workers) std::this_thread::yield();
        }
        require(state.fIsAParticleToKill==wanted,"Workers share selection state");
        step(actor,track,box);
        require(track.GetTrackStatus()==fAlive,"Killed at an internal boundary");
        step(actor,track,world,fPostStepDoItProc);
        require(track.GetTrackStatus()==fAlive,"Killed away from a boundary");
        step(actor,track,nullptr,fWorldBoundary);
        step(actor,track,nullptr);
        require(track.GetTrackStatus()==fAlive,"Invalid world-exit selection");
        step(actor,track,world);
        require((track.GetTrackStatus()==fStopAndKill)==wanted,"Wrong name selection");
      }
      require(state.fNbOfKilledParticles==1,"Wrong local count");
      actor.EndOfSimulationWorkerAction(nullptr);
      actor.EndOfSimulationWorkerAction(nullptr);
      geometry.DestroyWorkspace();
    });
    for (auto &thread:threads) thread.join();
    require(actor.GetNumberOfKilledParticles()==workers,"Wrong final count");
    require(other.GetNumberOfKilledParticles()==0,"Actor counters interfere");
    actor.StartSimulationAction();
    require(actor.GetNumberOfKilledParticles()==0,"Final count was not reset");
    std::cout << "PASS name LV state/selection: " << workers << " workers\n";
  }
}
