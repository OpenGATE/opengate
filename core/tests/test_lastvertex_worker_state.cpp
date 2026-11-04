// Native regression: exercise the real LV cache/callbacks concurrently without
// enabling transport MT before replay scheduling is ready.
#include "GateLastVertexInteractionSplittingActor.h"
#include <pybind11/embed.h>
#include <atomic>
#include <cstdlib>
#include <iostream>
#include <thread>

void require(bool condition, const char *message) {
  if (!condition) {
    std::cerr << message << std::endl;
    std::abort();
  }
}

int main() {
  py::scoped_interpreter python;
  for (int workers : {1, 2, 4, 8}) {
    py::dict info;
    info["name"] = "worker_state_test";
    GateLastVertexInteractionSplittingActor actor(info);
    GateLastVertexInteractionSplittingActor other(info);
    actor.StartSimulationAction();
    other.StartSimulationAction();
    std::atomic<int> ready{0};
    std::vector<std::thread> threads;
    for (int worker = 0; worker < workers; ++worker) {
      threads.emplace_back([&, worker] {
        auto &state = actor.fWorkerState.Get();
        auto &independent = other.fWorkerState.Get();
        require(&state != &independent, "Actors share worker state");
        require(state.fProcessToSplit == nullptr, "Uninitialized process");
        require(state.fSourceManager == nullptr, "Nonlocal source manager");
        require(state.fActiveSource == "None", "Nonlocal source name");
        LastVertexDataContainer root;
        root.SetTrackID(worker + 1);
        state.fTree.set_head(root);
        state.fIterator = state.fTree.begin_post();
        state.fListOfContainer.push_back(root);
        state.fListOfBiasedVolume.push_back(std::to_string(worker));
        state.fAAManager = new GateAcceptanceAngleManager();
        state.fAAManager->fNotAcceptedEvents = worker + 1;
        state.fNbOfBatchForExitingParticle = worker + 1;
        // Hold all live worker states at the same time before reading them.
        ++ready;
        while (ready.load() != workers)
          std::this_thread::yield();
        require(state.fIterator->GetTrackID() == worker + 1,
                "Workers share tree/iterator");
        require(state.fListOfContainer.front().GetTrackID() == worker + 1,
                "Workers share replay payload");
        require(state.fListOfBiasedVolume.front() == std::to_string(worker),
                "Workers share volume traversal state");
        require(state.fAAManager->fNotAcceptedEvents == worker + 1,
                "Workers share acceptance state");
        require(state.fNbOfBatchForExitingParticle == worker + 1,
                "Workers share batch counters");
        state.fActiveSource = std::to_string(worker);
        // Two simulated runs: counters must accumulate across their boundary.
        for (int run = 0; run < 2; ++run) {
          for (int event_id = 1; event_id <= 100; ++event_id) {
            G4Event event(event_id);
            actor.BeginOfEventAction(&event);
            actor.PreUserTrackingAction(nullptr);
          }
        }
        require(state.fActiveSource == std::to_string(worker),
                "Workers share current source name");
        require(state.fNumberOfEvent == 200, "Worker lost events");
        require(independent.fNumberOfEvent == 0, "Actors share counters");
        state.fRemovedParticle = worker + 1;
        state.fNumberOfReplayedEvent = 2 * (worker + 1);
        state.fNumberOfReplayedParticle = 3 * (worker + 1);
        actor.EndOfSimulationWorkerAction(nullptr);
        // Reduction is idempotent and frees the worker's acceptance manager.
        require(state.fAAManager == nullptr, "Acceptance manager not released");
        actor.EndOfSimulationWorkerAction(nullptr);
      });
    }
    for (auto &thread : threads)
      thread.join();
    const long sum = workers * (workers + 1) / 2;
    require(actor.GetNumberOfEvents() == 200 * workers, "Incorrect event reduction");
    require(actor.GetNumberOfKilledParticles() == sum, "Incorrect killed reduction");
    require(actor.GetNumberOfReplayedEvents() == 2 * sum, "Incorrect replay reduction");
    require(actor.GetNumberOfReplayedParticles() == 3 * sum, "Incorrect particle reduction");
    require(other.GetNumberOfEvents() == 0, "Actor totals interfere");
    actor.StartSimulationAction();
    require(actor.GetNumberOfEvents() == 0, "Totals not reset");
    std::cout << "PASS: " << workers << " workers" << std::endl;
  }
}
