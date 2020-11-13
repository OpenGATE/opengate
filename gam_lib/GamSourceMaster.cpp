/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#include <iostream>
#include "G4RunManager.hh"
#include "GamSourceMaster.h"
#include "G4SystemOfUnits.hh"

void GamSourceMaster::initialize(TimeIntervals simulation_times) {
    std::cout << "GamSourceMaster initialize " << simulation_times.size() << std::endl;
    m_simulation_times = simulation_times;
    m_current_simulation_time = 0;
    if (m_sources.empty()) { //FIXME pyside
        std::cout << "No sources" << std::endl;
        exit(0);
    }
    /*for (auto source:m_sources) {
        source->initialize(); // simulation times ? // FIXME maybe on py side because init
    }*/
}

void GamSourceMaster::add_source(GamVSource *source) {
    // FIXME
    //   auto name = std::any_cast<std::string>(source->user_info["name"]);
    //  std::cout << "Source Master add source " << name << std::endl;
    m_sources.push_back(source);
}

void GamSourceMaster::start() {
    std::cout << "Master start" << std::endl;
    for (unsigned int run_id = 0; run_id < m_simulation_times.size(); run_id++) {
        StartRun(run_id);
    }
}

void GamSourceMaster::StartRun(int run_id) {
    m_current_time_interval = m_simulation_times[run_id];
    // print info, log ? <-- maybe in the py side
    std::cout << "Start run " << run_id << " "
              << m_current_time_interval.first << " "
              << m_current_time_interval.second << std::endl;
    // init run for source ? needed ?
    PrepareNextSource();
    if (m_next_active_source == NULL) return; // FIXME ???
    //b = self.simulation.g4_RunManager.ConfirmBeamOnCondition()
    std::cout << "beam on " << INT32_MAX << std::endl;
    G4RunManager::GetRunManager()->BeamOn(INT32_MAX);
}

void GamSourceMaster::PrepareNextSource() {
    std::cout << "PrepareNextSource " << std::endl;
    m_next_active_source = NULL;//m_sources[0];
    double min_time = m_current_time_interval.first;
    double max_time = m_current_time_interval.second;
    std::cout << min_time << " " << max_time << " " << m_current_simulation_time << std::endl;
    std::cout << m_sources.size() << std::endl;
    for (auto source:m_sources) {
        auto t = source->PrepareNextTime(m_current_simulation_time);
        std::cout << "t" << t << std::endl;
        if (t >= min_time and t < max_time) {
            max_time = t;
            m_next_active_source = source;
        }
    }
    std::cout << "end prepare " << max_time << std::endl;
}

void GamSourceMaster::CheckForNextRun() {
    // FIXME Check active source NULL ?
    if (m_next_active_source == NULL) {
        std::cout << "Abort current run " << std::endl;
        G4RunManager::GetRunManager()->AbortRun(true);
    }
    // debug
    /*
    nb++;
    if (nb >= 200000) {
        std::cout << nb << std::endl;
        auto rm = G4RunManager::GetRunManager();
        rm->AbortRun(true);
    }
     */
}

void GamSourceMaster::GeneratePrimaries(G4Event *event) {
    std::cout << "GamSourceMaster GeneratePrimaries" << std::endl;

    // update the current time
    m_current_simulation_time = m_next_simulation_time;

    // shoot particle
    m_next_active_source->GeneratePrimaries(event, m_current_simulation_time);

    // prepare the next source
    PrepareNextSource();

    // check if this is not the end of the run
    CheckForNextRun();

}

