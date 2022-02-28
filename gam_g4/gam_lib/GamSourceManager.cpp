/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#include <iostream>
#include <pybind11/stl.h>
#include <pybind11/numpy.h>
#include <G4RunManager.hh>
#include <G4MTRunManager.hh>
#include <G4UImanager.hh>
#include <G4UIExecutive.hh>
#include <G4VisExecutive.hh>
#include <G4UIsession.hh>
#include <G4UnitsTable.hh>
#include "GamSourceManager.h"
#include "GamHelpers.h"
#include "GamHelpersDict.h"
#include "GamSignalHandler.h"

/* There will be one SourceManager per thread */

// Initialisation of static variable
int GamSourceManager::fVerboseLevel = 0;

GamSourceManager::GamSourceManager() {
    fStartNewRun = true;
    fNextRunId = 0;
    fUIEx = nullptr;
    fVisEx = nullptr;
    fVisualizationVerboseFlag = false;
    fVisualizationFlag = false;
    fVerboseLevel = 0;
}

GamSourceManager::~GamSourceManager() {
    delete fVisEx;
    // fUIEx is already deleted
}

void GamSourceManager::Initialize(TimeIntervals simulation_times, py::dict &options) {
    fSimulationTimes = simulation_times;
    fStartNewRun = true;
    fNextRunId = 0;
    fOptions = options;
    fVisualizationFlag = DictBool(options, "visu");
    fVisualizationVerboseFlag = DictBool(options, "visu_verbose");
    fVisCommands = DictVecStr(options, "visu_commands");
    fVerboseLevel = DictInt(options, "running_verbose_level");
    InstallSignalHandler();

    // Fake init of the EventModulo (will be changed in StartMasterThread or by the user)
    // thanks to /run/eventModulo 50000 1
    if (G4Threading::IsMultithreadedApplication()) {
        auto mt = static_cast<G4MTRunManager *>(G4RunManager::GetRunManager());
        mt->SetEventModulo(-1);
    }
}

void GamSourceManager::AddSource(GamVSource *source) {
    fSources.push_back(source);
}

void GamSourceManager::StartMasterThread() {
    // Create the main macro command
    // (only performed in the master thread)
    if (G4Threading::IsMultithreadedApplication()) {
        auto mt = static_cast<G4MTRunManager *>(G4RunManager::GetRunManager());
        if (mt->GetEventModulo() == -1) {
            mt->SetEventModulo(10000); // default value (not a big influence)
            // Much faster with mode 1 than with mode 0 (which is default)
            G4MTRunManager::SetSeedOncePerCommunication(1);
        }
    }

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
    // Prepare the run for all sources
    for (auto source: fSources) {
        source->PrepareNextRun();
    }
    // Check next time
    PrepareNextSource();
    if (fNextActiveSource == nullptr) {
        return;
    }
    fStartNewRun = false;
    Log(LogLevel_RUN, "Starting run {}\n", run_id);
}

void GamSourceManager::PrepareNextSource() {
    fNextActiveSource = nullptr;
    double min_time = fCurrentTimeInterval.first;
    double max_time = fCurrentTimeInterval.second;
    // Ask all sources their next time, keep the closest one
    for (auto source: fSources) {
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
    if (fNextActiveSource == nullptr) {
        G4RunManager::GetRunManager()->AbortRun(true); // FIXME true or false ?
        fStartNewRun = true;
        fNextRunId++;
        if (fNextRunId >= fSimulationTimes.size()) {
            // Sometimes, the source must clean some data in its own thread, not by the master thread
            // (for example with a G4SingleParticleSource object)
            // The CleanThread method is used for that.
            for (auto source: fSources) {
                source->CleanWorkerThread();
            }
        }
    }
}

void GamSourceManager::GeneratePrimaries(G4Event *event) {
    // Needed to initialize a new Run (all threads)
    if (fStartNewRun) PrepareRunToStart(fNextRunId);

    // update the current time
    fCurrentSimulationTime = fNextSimulationTime;

    // Sometimes (rarely), there is no active source,
    // so we create a fake geantino.
    // It may happen when the number of primary is fixed (with source.n = XX)
    // and several runs are used.
    if (fNextActiveSource == nullptr) {
        auto particle_table = G4ParticleTable::GetParticleTable();
        auto particle_def = particle_table->FindParticle("geantino");
        auto particle = new G4PrimaryParticle(particle_def);
        auto p = G4ThreeVector();
        auto vertex = new G4PrimaryVertex(p, fCurrentSimulationTime);
        vertex->SetPrimary(particle);
        event->AddPrimaryVertex(vertex);
    } else {
        // shoot particle
        fNextActiveSource->GeneratePrimaries(event, fCurrentSimulationTime);
        // log (after particle creation)
        if (LogLevel_EVENT <= GamSourceManager::fVerboseLevel) {
            auto prim = event->GetPrimaryVertex(0)->GetPrimary(0);
            std::string t = G4BestUnit(fCurrentSimulationTime, "Time");
            std::string e = G4BestUnit(prim->GetKineticEnergy(), "Energy");
            std::string s = fNextActiveSource->fName;
            Log(LogLevel_EVENT, "Event {} {} {} {} (source {})\n",
                event->GetEventID(), t, prim->GetParticleDefinition()->GetParticleName(),
                e, s);
        }
    }

    /*
    // For DEBUG
    auto name = event->GetPrimaryVertex(0)->GetPrimary(0)->GetParticleDefinition()->GetParticleName();
    auto E = event->GetPrimaryVertex(0)->GetPrimary(0)->GetKineticEnergy();
    std::cout << G4BestUnit(fCurrentSimulationTime, "Time") << " "
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
    char *argv[1]; // ok on osx
    //char **argv = new char*[1]; // not ok on osx
    fUIEx = new G4UIExecutive(1, argv, "qt");
    // FIXME does not work on Linux ? only OSX for the moment
    if (fVisEx == nullptr) {
        std::string v = "quiet";
        if (fVisualizationVerboseFlag) v = "all";
        fVisEx = new G4VisExecutive(v);
        fVisEx->Initialise();
        /* quiet,       // Nothing is printed.
         startup,       // Startup messages are printed...
         errors,        // ...and errors...
         warnings,      // ...and warnings...
         confirmations, // ...and confirming messages...
         parameters,    // ...and parameters of scenes and views...
         all            // ...and everything available. */
    }
    // Apply all visu commands
    auto uim = G4UImanager::GetUIpointer();
    for (const auto &x: fVisCommands) {
        uim->ApplyCommand(x);
    }
    // Needed to remove verbose
    uim->SetCoutDestination(&fSilent);
}

void GamSourceManager::StartVisualization() const {
    if (!fVisualizationFlag) return;
    fUIEx->SessionStart();
    delete fUIEx;
}

bool GamSourceManager::IsEndOfSimulationForWorker() const {
    return (fNextRunId >= fSimulationTimes.size());
}