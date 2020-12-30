/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#include <iostream>
#include "G4RunManager.hh"
#include "GamSourceManager.h"

GamSourceManager::GamSourceManager() {
    StartNewRun = true;
    NextRunId = 0;
}


void GamSourceManager::initialize(TimeIntervals simulation_times) {
    fSimulationTimes = simulation_times;
    StartNewRun = true;
    NextRunId = 0;
}

void GamSourceManager::add_source(GamVSource *source) {
    fSources.push_back(source);
}

void GamSourceManager::start_main_thread() {
    for (size_t run_id = 0; run_id < fSimulationTimes.size(); run_id++) {
        StartRun(run_id);
        G4RunManager::GetRunManager()->BeamOn(INT32_MAX);
    }
}

void GamSourceManager::StartRun(int run_id) {
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
    StartNewRun = false;
}

void GamSourceManager::PrepareNextSource() {
    fNextActiveSource = NULL;
    double min_time = fCurrentTimeInterval.first;
    double max_time = fCurrentTimeInterval.second;
    // Ask all sources their next time, keep the closest one
    for (auto source:fSources) {
        auto t = source->PrepareNextTime(fCurrentSimulationTime);
        if (t >= min_time and t < max_time) {
            max_time = t;
            fNextActiveSource = source;
            fNextSimulationTime = t;
        }
    }
    // If no next time in the current interval, active source is NULL
}

void GamSourceManager::CheckForNextRun() {
    // FIXME Check active source NULL ?
    if (fNextActiveSource == NULL) {
        G4RunManager::GetRunManager()->AbortRun(true);
        StartNewRun = true;
        NextRunId++;
    }
}

void GamSourceManager::GeneratePrimaries(G4Event *event) {
    // Needed to initialize a new Run (all threads)
    if (StartNewRun) StartRun(NextRunId);

    // update the current time
    fCurrentSimulationTime = fNextSimulationTime;

    // shoot particle
    fNextActiveSource->GeneratePrimaries(event, fCurrentSimulationTime);

    // prepare the next source
    PrepareNextSource();

    // check if this is not the end of the run
    CheckForNextRun();
}

