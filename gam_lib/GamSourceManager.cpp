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
#include "G4UnitsTable.hh"
#include "GamSourceManager.h"
#include "GamHelpers.h"
#include "GamDictHelpers.h"

/* There will be one SourceManager per thread */

G4Mutex sm_mutex = G4MUTEX_INITIALIZER;


GamSourceManager::GamSourceManager() {
    auto & rp = fRunProperties.Get();
    rp.fStartNewRun = true;
    rp.fNextRunId = 0;
    fUIEx = nullptr;
    fVisEx = nullptr;
    fVisualizationVerboseFlag = false;
    fVisualizationFlag = false;
}

GamSourceManager::~GamSourceManager() {
    delete fVisEx;
    // fUIEx is already deleted
}

void GamSourceManager::Initialize(TimeIntervals simulation_times, py::dict &vis_options) {
    fSimulationTimes = simulation_times;
    auto & rp = fRunProperties.Get();
    rp.fStartNewRun = true;
    rp.fNextRunId = 0;
    fOptions = vis_options;
    fVisualizationFlag = DictBool(vis_options, "g4_visualisation_flag");
    fVisualizationVerboseFlag = DictBool(vis_options, "g4_visualisation_verbose_flag");
    fVisCommands = DictVecStr(vis_options, "g4_vis_commands");
}

void GamSourceManager::AddSource(GamVSource *source) {
    DDD("AddSource");
    //if (G4Threading::G4GetThreadId() == -1) return;
    auto & rp = fRunProperties.Get();
    /*auto c = source->Clone();
    DDD(c);
    DDD(c->Dump());
    rp.fSources.push_back(c);
     */
    DDD(source->Dump());
    rp.fSources.push_back(source);
}

void GamSourceManager::StartMainThread() {
    DDD("StartMainThread");
    // Create the main macro command
    // (only performed in the master thread)
    std::ostringstream oss;
    oss << "/run/beamOn " << INT32_MAX;
    std::string run = oss.str();
    // Loop on run
    for (size_t run_id = 0; run_id < fSimulationTimes.size(); run_id++) {
        DDD(run_id);
        PrepareRunToStart(run_id);
        InitializeVisualization();
        auto uim = G4UImanager::GetUIpointer();
        DDD("BeamOn");
        uim->ApplyCommand(run);
        DDD("After BeamOn");
        StartVisualization();
    }
}

void GamSourceManager::PrepareRunToStart(int run_id) {
    DDD(run_id);
    auto & rp = fRunProperties.Get();
    // NOPE G4AutoLock l(&sm_mutex);
    // set the current time interval
    rp.fCurrentTimeInterval = fSimulationTimes[run_id];
    // set the current time
    rp.fCurrentSimulationTime = rp.fCurrentTimeInterval.first;
    // Prepare the run for all sources
    for (auto source:rp.fSources) {
        DDD(source);
        DDD(source->Dump());
        source->PrepareNextRun();
    }
    // Check next time
    PrepareNextSource();
    if (rp.fNextActiveSource == NULL) {
        DDD("next source null");
        return;
    }
    rp.fStartNewRun = false;
}

void GamSourceManager::PrepareNextSource() {
    //G4AutoLock l(&sm_mutex);
    auto & rp = fRunProperties.Get();
    rp.fNextActiveSource = NULL;
    double min_time = rp.fCurrentTimeInterval.first;
    double max_time = rp.fCurrentTimeInterval.second;
    // Ask all sources their next time, keep the closest one
    for (auto source:rp.fSources) {
        auto t = source->PrepareNextTime(rp.fCurrentSimulationTime);
        if ((t >= min_time) && (t < max_time)) {
            max_time = t;
            rp.fNextActiveSource = source;
            rp.fNextSimulationTime = t;
        }
    }
    // If no next time in the current interval, active source is NULL
}

void GamSourceManager::CheckForNextRun() {
    DDD("CheckForNextRun");
    //G4AutoLock l(&sm_mutex);
    auto & rp = fRunProperties.Get();
    DDD(rp.fNextActiveSource);
    if (rp.fNextActiveSource == NULL) {
        // abort only for one thread (?)
        //if (G4Threading::G4GetThreadId() == 0)
        DDD("AbortRun");
        G4RunManager::GetRunManager()->AbortRun(true); // FIXME or false ?
        rp.fStartNewRun = true;
        rp.fNextRunId++;
        if (rp.fNextRunId >= fSimulationTimes.size()) {
            // Sometimes, the source must clean some data in its own thread, not by the master thread
            // (for example with a G4SingleParticleSource object)
            // The CleanThread method is used for that.
            for (auto source:rp.fSources) {
                DDD(source);
                source->CleanInThread();
            }
            // FIXME --> Maybe add here actor SimulationStopInThread
        }
    }
}

void GamSourceManager::GeneratePrimaries(G4Event *event) {
    //G4AutoLock l(&sm_mutex);
    DDD("GeneratePrimaries");
    auto & rp = fRunProperties.Get();
    DDD(&rp);
    DDD(rp.fStartNewRun);
    // Needed to initialize a new Run (all threads)
    if (rp.fStartNewRun) PrepareRunToStart(rp.fNextRunId);

    // update the current time
    rp.fCurrentSimulationTime = rp.fNextSimulationTime;

    // Sometimes, there is no active source FIXME  --> geantino
    if (rp.fNextActiveSource == NULL) {
        DDD("geantino")
        auto particle_table = G4ParticleTable::GetParticleTable();
        auto particle_def = particle_table->FindParticle("geantino");
        auto particle = new G4PrimaryParticle(particle_def);
        auto p = G4ThreeVector();
        auto vertex = new G4PrimaryVertex(p, rp.fCurrentSimulationTime);
        vertex->SetPrimary(particle);
        event->AddPrimaryVertex(vertex);
    } else {
        // shoot particle
        rp.fNextActiveSource->GeneratePrimaries(event, rp.fCurrentSimulationTime);
    }

    /*
    // For DEBUG
    auto name = event->GetPrimaryVertex(0)->GetPrimary(0)->GetParticleDefinition()->GetParticleName();
    auto E = event->GetPrimaryVertex(0)->GetPrimary(0)->GetKineticEnergy();
    std::cout << G4BestUnit(rp.fCurrentSimulationTime, "Time") << " "
              << event->GetEventID() << " "
              << name << " "
              << G4BestUnit(E, "Energy") << std::endl;
    */

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

