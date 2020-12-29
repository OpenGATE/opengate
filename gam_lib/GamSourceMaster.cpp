/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#include <iostream>
#include "G4RunManager.hh"
#include "GamSourceMaster.h"

GamSourceMaster::GamSourceMaster() {
    DDD("Construction GamSourceMaster");
    StartNewRun = true;
    NextRunId = 0;
}


void GamSourceMaster::initialize(TimeIntervals simulation_times) {
    DDD("init");
    m_simulation_times = simulation_times;
}

void GamSourceMaster::add_source(GamVSource *source) {
    DDD("add source");
    m_sources.push_back(source);
}

void GamSourceMaster::start() {
    DDD("GamSourceMaster::start");
    for (size_t run_id = 0; run_id < m_simulation_times.size(); run_id++) {
        DDD(run_id);
        StartRun(run_id);
        DDD("G4RunManager::GetRunManager()->BeamOn");
        G4RunManager::GetRunManager()->BeamOn(INT32_MAX);
    }
}

void GamSourceMaster::StartRun(int run_id) {
    DDD("GamSourceMaster::StartRun");
    // set the current time interval
    m_current_time_interval = m_simulation_times[run_id];
    // set the current time
    m_current_simulation_time = m_current_time_interval.first;
    // Prepare the run for all source
    for (auto source:m_sources) {
        DDD(source->name);
        source->PrepareNextRun();
    }
    // Check next time
    PrepareNextSource();
    if (m_next_active_source == NULL) return;
    // Go !
    /*if (G4Threading::G4GetThreadId() == -1) {
        DDD("G4RunManager::GetRunManager()->BeamOn");
        //G4RunManager::GetRunManager()->BeamOn(INT32_MAX);
    }*/
    //G4RunManager::GetRunManager()->BeamOn(50);
    StartNewRun = false;
}

void GamSourceMaster::PrepareNextSource() {
    //DDD("PrepareNextSource");
    m_next_active_source = NULL;
    double min_time = m_current_time_interval.first;
    double max_time = m_current_time_interval.second;
    // Ask all sources their next time, keep the closest one
    for (auto source:m_sources) {
        auto t = source->PrepareNextTime(m_current_simulation_time);
        if (t >= min_time and t < max_time) {
            max_time = t;
            m_next_active_source = source;
            m_next_simulation_time = t;
        }
    }
    // If no next time in the current interval, active source is NULL
}

void GamSourceMaster::CheckForNextRun() {
    // FIXME Check active source NULL ?
    //DDD("CheckForNextRun");
    if (m_next_active_source == NULL) {
        DDD("Before AbortRun");
        // FIXME debug
        for (auto source:m_sources) {
            DDD(source->m_events_per_run[0]);
        }
        G4RunManager::GetRunManager()->AbortRun(true);
        StartNewRun = true;
        NextRunId++;
    }
}

void GamSourceMaster::GeneratePrimaries(G4Event *event) {
    if (StartNewRun) StartRun(NextRunId);

    //DDD("GeneratePrimaries");
    //DDD(event->GetEventID());

    // update the current time
    m_current_simulation_time = m_next_simulation_time;

    // shoot particle
    m_next_active_source->GeneratePrimaries(event, m_current_simulation_time);

    // prepare the next source
    PrepareNextSource();

    // check if this is not the end of the run
    CheckForNextRun();
}

