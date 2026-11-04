// Fail before splitting or replay access when runtime state is inconsistent.
#include "GateLastVertexInteractionSplittingActor.h"
#include "GateLastVertexSource.h"
#include <G4Geantino.hh>
#include <G4ProcessManager.hh>
#include <G4Transportation.hh>
#include <G4TouchableHistory.hh>
#include <pybind11/embed.h>
#include <cstdlib>
#include <functional>
#include <iostream>

void require(bool value, const char *message) {
  if (!value) { std::cerr << message << std::endl; std::abort(); }
}
void fails(const std::function<void()> &call, const std::string &message) {
  try { call(); }
  catch (const std::runtime_error &error) {
    require(std::string(error.what()).find(message)!=std::string::npos,
            "Missing diagnostic context");
    return;
  }
  require(false,"Expected a fatal error");
}
LastVertexDataContainer replay() {
  LastVertexDataContainer container;
  container.SetContainerToSplit(SimpleContainer(
      "Transportation",1,{0,0,1},{0,0,0},{0,0,0},"geantino",1,0,0,
      "None",1,{0,0,0},G4TouchableHandle(new G4TouchableHistory())));
  return container;
}
int main() {
  py::scoped_interpreter python;
  py::dict info; info["name"]="fail_fast_test";
  GateLastVertexInteractionSplittingActor actor(info);
  auto *particle=G4Geantino::GeantinoDefinition();
  fails([&]{actor.GetProcessFromProcessName("missing_particle","compt");},
        "particle 'missing_particle' not found");
  particle->SetProcessManager(nullptr);
  fails([&]{actor.GetProcessFromProcessName("geantino","compt");},
        "no process manager for particle 'geantino'");
  auto *manager=new G4ProcessManager(particle);
  particle->SetProcessManager(manager);
  auto *transportation=new G4Transportation;
  manager->AddProcess(transportation);
  require(actor.GetProcessFromProcessName("geantino","Transportation")==transportation,
          "Valid process lookup changed");
  fails([&]{actor.GetProcessFromProcessName("geantino","missing_process");},
        "process 'missing_process' not found for particle 'geantino'");
  std::cout << "PASS process lookup: valid/missing process, particle and manager\n";

  // The existing tree search must find the current track, not reuse a stale iterator.
  auto &state = actor.fWorkerState.Get();
  auto visit = [&](int id, int parent, bool firstStep) {
    G4Track track(new G4DynamicParticle(particle,{0,0,1},1),0,{});
    track.SetTrackID(id); track.SetParentID(parent);
    G4Step step; step.SetTrack(&track);
    state.fIsFirstStep = firstStep;
    actor.FillOfDataTree(&step);
  };
  visit(1,0,true);
  require(state.fIterator->GetTrackID()==1,"Root lookup changed");
  visit(2,1,true);
  require(state.fIterator->GetTrackID()==2,"Child lookup changed");
  visit(2,1,false);
  require(state.fIterator->GetTrackID()==2,"Later step changed the iterator");
  fails([&]{visit(3,999,true);},"track 3 (parent 999) absent from genealogy tree");
  require(state.fIterator->GetTrackID()==2,"Missing track corrupted the prior iterator");
  state.fIterator = state.fTree.end_post();
  fails([&]{visit(4,999,true);},"track 4 (parent 999) absent from genealogy tree");
  std::cout << "PASS genealogy: roots/children work; missing tracks fail before access\n";

  GateLastVertexSource source;
  source.fName="arbitrary_replay_name";
  source.SetNumberOfEventToSimulate(2);
  source.SetNumberOfGeneratedEvent(0);
  source.SetListOfVertexToSimulate({replay()});
  G4Event invalid;
  fails([&]{source.GeneratePrimaries(&invalid,0);},"replay queue desynchronised");
  require(invalid.GetNumberOfPrimaryVertex()==0 && source.GetTotalReplayedEvents()==0,
          "Invalid queue generated a primary");
  require(source.GetNumberOfGeneratedEvent()==0,"Invalid queue advanced its cursor");
  source.SetListOfVertexToSimulate({replay(),replay()});
  fails([&]{source.GenerateOnePrimary(&invalid,0,2);},"index=2");
  fails([&]{source.GenerateOnePrimary(&invalid,0,-1);},"index=-1");
  source.SetNumberOfEventToSimulate(1);
  fails([&]{source.GeneratePrimaries(&invalid,0);},"expected=1, size=2");
  source.SetNumberOfEventToSimulate(2);
  {
    G4Event first;
    source.GeneratePrimaries(&first,0);
    require(first.GetNumberOfPrimaryVertex()==1 && source.GetTotalReplayedEvents()==1,
            "First valid replay changed");
  }
  {
    G4Event last;
    source.GeneratePrimaries(&last,0);
    require(last.GetNumberOfPrimaryVertex()==1 && source.GetTotalReplayedEvents()==2,
            "Last valid replay changed");
    require(!source.HasPendingEvents(),"Valid queue did not drain");
  }
  {
    G4Event fallback;
    source.GeneratePrimaries(&fallback,0);
    require(fallback.GetNumberOfPrimaryVertex()==1 && source.GetTotalReplayedEvents()==2,
            "Exhausted-queue geantino behavior changed");
  }
  std::cout << "PASS replay access: bad size/index fail; valid and exhausted queues work\n";
}
