// Exercise the existing LV retry code without changing its limits or scheduling.
#include "GateLastVertexInteractionSplittingActor.h"
#include <G4Geantino.hh>
#include <G4StackManager.hh>
#include <G4VEmProcess.hh>
#include <pybind11/embed.h>
#include <cstdlib>
#include <iostream>

void require(bool value,const char *message) {
  if (!value) {std::cerr<<message<<std::endl;std::abort();}
}
// Controlled process result; the real LV dispatch/acceptance/stack code is used.
class ControlledCompton : public G4VEmProcess {
public:
  ControlledCompton() : G4VEmProcess("compt") {}
  GateAcceptanceAngleManager *acceptance=nullptr;
  int calls=0, reject=0;
  G4ParticleChangeForGamma result;
  void InitialiseProcess(const G4ParticleDefinition *) override {}
  G4VParticleChange *PostStepDoIt(const G4Track &track,const G4Step &) override {
    ++calls;
    acceptance->fEnabledFlag=calls<=reject;
    result.InitializeForPostStep(track);
    return &result;
  }
};
int main() {
  py::scoped_interpreter python;
  py::dict info;info["name"]="attempt_limit_test";
  GateLastVertexInteractionSplittingActor actor(info);
  auto &state=actor.fWorkerState.Get();
  G4StackManager stack;
  ControlledCompton process;
  state.fStackManager=&stack;
  state.fAAManager=new GateAcceptanceAngleManager;
  process.acceptance=state.fAAManager;
  state.fTrackToSplit=new G4Track(
      new G4DynamicParticle(G4Geantino::GeantinoDefinition(),{0,0,1},1),0,{});
  state.fWeight=1;
  state.fProcessNameToSplit="compt";
  state.fProcessToSplit=&process;
  actor.fNbOfMaxBatchPerEvent=300;
  G4Step step;
  LastVertexDataContainer container;
  // Normal successive batches: the configured 300 threshold is effective.
  for(int batch=1;batch<=301;++batch) {
    actor.CreateNewParticleAtTheLastVertex(&step,container,1);
    require(stack.GetNTotalTrack()==(batch<=300?1:0),"Normal batch cutoff changed");
    stack.clear();
  }
  require(state.fRemovedParticle==1,"Normal cutoff count changed");
  std::cout<<"PASS normal successive batches: 300 retained, batch 301 cleared\n";

  // Rejected recursive calls defer the cutoff until a call returns.
  process.calls=0;process.reject=301;
  state.fAAManager->fMaxNotAcceptedEvents=100000;
  state.fAAManager->fNotAcceptedEvents=0;
  state.fNbOfBatchForExitingParticle=0;state.fRemovedParticle=0;
  actor.CreateNewParticleAtTheLastVertex(&step,container,1);
  require(process.calls==302 && state.fNbOfBatchForExitingParticle==302,
          "Recursive-path behavior changed");
  require(stack.GetNTotalTrack()==0,"Recursive unwind failed to clear stack");
  std::cout<<"OBSERVED recursive all-rejected path: 302 calls before cutoff, "
           <<state.fRemovedParticle<<" unwind removals\n";

  // With production defaults, the angular guard terminates an impossible direction.
  process.calls=0;process.reject=100000;
  state.fAAManager->fMaxNotAcceptedEvents=10000;
  state.fAAManager->fNotAcceptedEvents=0;
  state.fNbOfBatchForExitingParticle=0;state.fRemovedParticle=0;
  bool failed=false;
  try {actor.CreateNewParticleAtTheLastVertex(&step,container,500);}
  catch(const std::runtime_error &e) {
    failed=std::string(e.what()).find("AcceptanceAngleTest")!=std::string::npos;
  }
  require(failed && process.calls==10002,"Angular rejection guard did not stop retries");
  std::cout<<"PASS default all-rejected guard: "<<process.calls<<" proposals, "
           <<state.fNbOfBatchForExitingParticle<<" complete batches; explicit error\n";
  // Pointer lifetime remains managed by the actor for its own track/AA objects.
}
