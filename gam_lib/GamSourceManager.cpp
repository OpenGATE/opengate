/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#include <iostream>
#include <pybind11/stl.h>
#include <pybind11/numpy.h>
#include "G4RunManager.hh"
#include "G4UImanager.hh"
#include "G4UIExecutive.hh"
#include "G4VisExecutive.hh"
#include "G4UIsession.hh"
#include "GamSourceManager.h"
#include "GamDictHelpers.h"

/* There will be one SourceManager per thread */

GamSourceManager::GamSourceManager() {
    fStartNewRun = true;
    fNextRunId = 0;
    fUIEx = nullptr;
    fVisEx = nullptr;
    fVisualizationVerboseFlag = false;
    fVisualizationFlag = false;
}

GamSourceManager::~GamSourceManager() {
    DDD("destructor source m");
    delete fVisEx;
    // fUIEx is already deleted
}

void GamSourceManager::Initialize(TimeIntervals simulation_times, py::dict &options) {

    fSimulationTimes = simulation_times;
    fStartNewRun = true;
    fNextRunId = 0;
    fOptions = options;
    fVisualizationFlag = DictBool(fOptions, "g4_visualisation_flag");
    fVisualizationVerboseFlag = DictBool(fOptions, "g4_visualisation_verbose_flag");
    fVisCommands = DictVecStr(fOptions, "g4_vis_commands");
}

void GamSourceManager::AddSource(GamVSource *source) {
    fSources.push_back(source);
}

void GamSourceManager::StartMainThread() {
    // Create the main macro command
    std::ostringstream oss;
    oss << "/run/beamOn " << INT32_MAX;
    std::string run = oss.str();
    // Loop on run
    for (size_t run_id = 0; run_id < fSimulationTimes.size(); run_id++) {
        PrepareRunToStart(run_id);
        InitializeVisualization();
        auto uim = G4UImanager::GetUIpointer();
        uim->ApplyCommand(run);
        StartVisualization();
    }
}

void GamSourceManager::PrepareRunToStart(int run_id) {
    // set the current time interval
    fCurrentTimeInterval = fSimulationTimes[run_id];
    // set the current time
    fCurrentSimulationTime = fCurrentTimeInterval.first;
    // Prepare the run for all source
    for (auto source:fSources) {
        source->PrepareNextRun();
    }
    // Check next time
    PrepareNextSource();
    if (fNextActiveSource == NULL) return;
    fStartNewRun = false;
}

void GamSourceManager::PrepareNextSource() {
    fNextActiveSource = NULL;
    double min_time = fCurrentTimeInterval.first;
    double max_time = fCurrentTimeInterval.second;
    // Ask all sources their next time, keep the closest one
    for (auto source:fSources) {
        auto t = source->PrepareNextTime(fCurrentSimulationTime);
        if ((t >= min_time) && (t < max_time)) {
            max_time = t;
            fNextActiveSource = source;
            fNextSimulationTime = t;
        }
    }
    // If no next time in the current interval, active source is NULL
}

void GamSourceManager::CheckForNextRun() {
    if (fNextActiveSource == NULL) {
        G4RunManager::GetRunManager()->AbortRun(true);
        fStartNewRun = true;
        fNextRunId++;
        if (fNextRunId == fSimulationTimes.size()) {
            // Sometimes, the source must clean some data in its own thread, not by the master thread
            // (for example with a G4SingleParticleSource object)
            // The CleanThread method is used for that.
            for (auto source:fSources) {
                source->CleanInThread();
            }
            // FIXME --> Maybe add here actor SimulationStopInThread
        }
    }
}

void GamSourceManager::GeneratePrimaries(G4Event *event) {
    // Needed to initialize a new Run (all threads)
    if (fStartNewRun) PrepareRunToStart(fNextRunId);

    // update the current time
    fCurrentSimulationTime = fNextSimulationTime;

    // shoot particle
    fNextActiveSource->GeneratePrimaries(event, fCurrentSimulationTime);

    // prepare the next source
    PrepareNextSource();

    // check if this is not the end of the run
    CheckForNextRun();
}

void GamSourceManager::InitializeVisualization() {
    if (!fVisualizationFlag) return;
    char *argv[1];
    fUIEx = new G4UIExecutive(1, argv);
    if (fVisEx == nullptr) {
        std::string v = "quiet";
        if (fVisualizationVerboseFlag) v = "all";
        fVisEx = new G4VisExecutive(v);
        fVisEx->Initialise();
        /* quiet,       // Nothing is printed.
         startup,       // Startup and endup messages are printed...
         errors,        // ...and errors...
         warnings,      // ...and warnings...
         confirmations, // ...and confirming messages...
         parameters,    // ...and parameters of scenes and views...
         all            // ...and everything available. */
    }
    // Apply all visu commands
    auto uim = G4UImanager::GetUIpointer();
    for (auto x:fVisCommands) {
        uim->ApplyCommand(x);
    }
    // Needed to remove verbose
    uim->SetCoutDestination(&fSilent);
}

void GamSourceManager::StartVisualization() {
    if (!fVisualizationFlag) return;
    fUIEx->SessionStart();
    delete fUIEx;
}

