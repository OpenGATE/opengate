/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#include <iostream>
#include "G4RunManager.hh"
#include "G4UnitsTable.hh"
#include "G4UImanager.hh"
#include "G4UIExecutive.hh"
#include "GamSourceMaster.h"

void GamSourceMaster::initialize(TimeIntervals simulation_times) {
    m_simulation_times = simulation_times;
}

void GamSourceMaster::add_source(GamVSource *source) {
    m_sources.push_back(source);
}

void GamSourceMaster::start() {
    for (size_t run_id = 0; run_id < m_simulation_times.size(); run_id++) {
        StartRun(run_id);
    }
}

void GamSourceMaster::StartRun(int run_id) {
    // set the current time interval
    m_current_time_interval = m_simulation_times[run_id];
    // set the current time
    m_current_simulation_time = m_current_time_interval.first;
    // Prepare the run for all source
    for (auto source:m_sources)
        source->PrepareNextRun();
    // Check next time
    PrepareNextSource();
    if (m_next_active_source == NULL) return;
    // FIXME VISUALIZATION
    //self.simulation.g4_apply_command(f'/run/beamOn {self.max_int}')
    //        self.simulation.g4_ui_executive.SessionStart()
    //self.g4_ui = g4.G4UImanager.GetUIpointer()
    //        self.g4_ui.ApplyCommand(command)

    /*
    auto ui = G4UImanager::GetUIpointer();
    DD("before beam on");
    ui->ApplyCommand("/run/beamOn 2147483647");
    DD("ici");
     */
    /*
    //self.simulation.g4_ui_executive.SessionStart()
    char *argv[1];
    DD("la");
    auto uie = new G4UIExecutive(1, argv);
    DD("before start")
    uie->SessionStart();
    DD("after start")
    //G4RunManager::GetRunManager()->BeamOn(INT32_MAX);
     */
    G4RunManager::GetRunManager()->BeamOn(INT32_MAX);
}

void GamSourceMaster::PrepareNextSource() {
    m_next_active_source = NULL;//m_sources[0];
    double min_time = m_current_time_interval.first;
    double max_time = m_current_time_interval.second;
    for (auto source:m_sources) {
        auto t = source->PrepareNextTime(m_current_simulation_time);
        if (t >= min_time and t < max_time) {
            max_time = t;
            m_next_active_source = source;
            m_next_simulation_time = t;
        }
    }
}

void GamSourceMaster::CheckForNextRun() const {
    // FIXME Check active source NULL ?
    if (m_next_active_source == NULL) {
        G4RunManager::GetRunManager()->AbortRun(true);
    }
}

void GamSourceMaster::GeneratePrimaries(G4Event *event) {
    // update the current time
    m_current_simulation_time = m_next_simulation_time;

    // shoot particle
    m_next_active_source->GeneratePrimaries(event, m_current_simulation_time);

    // prepare the next source
    PrepareNextSource();

    // check if this is not the end of the run
    CheckForNextRun();
}

