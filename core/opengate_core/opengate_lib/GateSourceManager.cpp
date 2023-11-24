/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#include <iostream>
#include <pybind11/numpy.h>

#ifdef USE_GDML

#include <G4GDMLParser.hh>

#endif

#include "GateHelpers.h"
#include "GateHelpersDict.h"
#include "GateSignalHandler.h"
#include "GateSourceManager.h"
#include <G4MTRunManager.hh>
#include <G4RunManager.hh>
#include <G4TransportationManager.hh>
#include <G4UIExecutive.hh>
#include <G4UImanager.hh>
#include <G4UnitsTable.hh>

/* There will be one SourceManager per thread */

// Initialisation of static variable
int GateSourceManager::fVerboseLevel = 0;

GateSourceManager::GateSourceManager() {
  fUIEx = nullptr;
  fVisEx = nullptr;
  fVisualizationVerboseFlag = false;
  fVisualizationFlag = false;
  fVisualizationTypeFlag = "qt";
  fVisualizationFile = "g4writertest.gdml";
  fVerboseLevel = 0;
  fUserEventInformationFlag = false;
  auto &l = fThreadLocalData.Get();
  l.fStartNewRun = true;
  l.fNextRunId = 0;
  l.fUserEventInformation = nullptr;
  l.fCurrentSimulationTime = 0;
  l.fNextActiveSource = nullptr;
  l.fNextSimulationTime = 0;
}

GateSourceManager::~GateSourceManager() {
  delete fVisEx;
  // fUIEx is already deleted
}

void GateSourceManager::Initialize(TimeIntervals simulation_times,
                                   py::dict &options) {
  fSimulationTimes = simulation_times;
  auto &l = fThreadLocalData.Get();
  l.fStartNewRun = true;
  l.fNextRunId = 0;
  fOptions = options;
  fVisualizationFlag = DictGetBool(options, "visu");
  fVisualizationVerboseFlag = DictGetBool(options, "visu_verbose");
  fVisualizationTypeFlag = DictGetStr(options, "visu_type");
  fVisualizationFile = DictGetStr(options, "visu_filename");
  if (fVisualizationTypeFlag == "vrml" ||
      fVisualizationTypeFlag == "vrml_file_only")
    fVisCommands = DictGetVecStr(options, "visu_commands_vrml");
  else if (fVisualizationTypeFlag == "gdml" ||
           fVisualizationTypeFlag == "gdml_file_only")
    fVisCommands = DictGetVecStr(options, "visu_commands_gdml");
  else
    fVisCommands = DictGetVecStr(options, "visu_commands");
  fVerboseLevel = DictGetInt(options, "running_verbose_level");
  InstallSignalHandler();

  // Fake init of the EventModulo (will be changed in StartMasterThread or by
  // the user) thanks to /run/eventModulo 50000 1
  if (G4Threading::IsMultithreadedApplication()) {
    auto mt = static_cast<G4MTRunManager *>(G4RunManager::GetRunManager());
    mt->SetEventModulo(-1);
  }
}

void GateSourceManager::AddSource(GateVSource *source) {
  fSources.push_back(source);
}

void GateSourceManager::SetActors(std::vector<GateVActor *> &actors) {
  fActors = actors;
}

void GateSourceManager::StartMasterThread() {
  // Create the main macro command
  // (only performed in the master thread)
  if (G4Threading::IsMultithreadedApplication()) {
    // (static is needed, dynamic_cast lead to seg fault)
    auto mt = dynamic_cast<G4MTRunManager *>(G4RunManager::GetRunManager());
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
  auto &l = fThreadLocalData.Get();
  l.fStartNewRun = true;
  for (size_t run_id = 0; run_id < fSimulationTimes.size(); run_id++) {
    // Start Begin Of Run for MasterThread
    // (both for multi-thread and mono-thread app)
    // The conventional (threaded) BeginOfRun will be called
    // for all threads by the Action loop
    for (auto &actor : fActors) {
      actor->BeginOfRunActionMasterThread(run_id);
    }
    InitializeVisualization();
    auto *uim = G4UImanager::GetUIpointer();
    uim->ApplyCommand(run);
    StartVisualization();
  }
}

void GateSourceManager::PrepareRunToStart(int run_id) {
  /*
   In MT mode, this function (PrepareRunToStart) is called
   by Master thread AND by workers
   */
  // set the current time interval
  auto &l = fThreadLocalData.Get();
  l.fCurrentTimeInterval = fSimulationTimes[run_id];
  // set the current time
  l.fCurrentSimulationTime = l.fCurrentTimeInterval.first;
  // Prepare the run for all sources
  for (auto *source : fSources) {
    source->PrepareNextRun();
  }
  // Check next time
  PrepareNextSource();
  if (l.fNextActiveSource == nullptr) {
    return;
  }
  l.fStartNewRun = false;
  Log(LogLevel_RUN, "Starting run {} ({})\n", run_id,
      G4Threading::IsMasterThread() == TRUE
          ? "master"
          : std::to_string(G4Threading::G4GetThreadId()));
}

void GateSourceManager::PrepareNextSource() {
  auto &l = fThreadLocalData.Get();
  l.fNextActiveSource = nullptr;
  double min_time = l.fCurrentTimeInterval.first;
  double max_time = l.fCurrentTimeInterval.second;
  // Ask all sources their next time, keep the closest one
  for (auto *source : fSources) {
    auto t = source->PrepareNextTime(l.fCurrentSimulationTime);
    if ((t >= min_time) && (t < max_time)) {
      max_time = t;
      l.fNextActiveSource = source;
      l.fNextSimulationTime = t;
    }
  }
  // If no next time in the current interval, active source is NULL
}

void GateSourceManager::CheckForNextRun() {
  auto &l = fThreadLocalData.Get();
  if (l.fNextActiveSource == nullptr) {
    G4RunManager::GetRunManager()->AbortRun(true); // FIXME true or false ?
    l.fStartNewRun = true;
    l.fNextRunId++;
    if (l.fNextRunId >= fSimulationTimes.size()) {
      // Sometimes, the source must clean some data in its own thread, not by
      // the master thread (for example with a G4SingleParticleSource object)
      // The CleanThread method is used for that.
      for (auto *source : fSources) {
        source->CleanWorkerThread();
      }
    }
  }
}

void GateSourceManager::GeneratePrimaries(G4Event *event) {
  auto &l = fThreadLocalData.Get();
  // Needed to initialize a new Run (all threads)
  if (l.fStartNewRun) {
    PrepareRunToStart(l.fNextRunId);
  }

  // update the current time
  l.fCurrentSimulationTime = l.fNextSimulationTime;

  // Sometimes (rarely), there is no active source,
  // so we create a fake geantino particle
  // It may happen when the number of primary is fixed (with source.n = XX)
  // and several runs are used.
  if (l.fNextActiveSource == nullptr) {
    auto *particle_table = G4ParticleTable::GetParticleTable();
    auto *particle_def = particle_table->FindParticle("geantino");
    auto *particle = new G4PrimaryParticle(particle_def);
    auto p = G4ThreeVector();
    auto *vertex = new G4PrimaryVertex(p, l.fCurrentSimulationTime);
    vertex->SetPrimary(particle);
    event->AddPrimaryVertex(vertex);
  } else {
    // shoot particle
    l.fNextActiveSource->GeneratePrimaries(event, l.fCurrentSimulationTime);
    // log (after particle creation)
    if (LogLevel_EVENT <= GateSourceManager::fVerboseLevel) {
      auto *prim = event->GetPrimaryVertex(0)->GetPrimary(0);
      std::string t = G4BestUnit(l.fCurrentSimulationTime, "Time");
      std::string e = G4BestUnit(prim->GetKineticEnergy(), "Energy");
      std::string s = l.fNextActiveSource->fName;
      Log(LogLevel_EVENT, "Event {} {} {} {} {:.2f} {:.2f} {:.2f} ({})\n",
          event->GetEventID(), t,
          prim->GetParticleDefinition()->GetParticleName(), e,
          event->GetPrimaryVertex(0)->GetPosition()[0],
          event->GetPrimaryVertex(0)->GetPosition()[1],
          event->GetPrimaryVertex(0)->GetPosition()[2], s);
    }
  }

  // Add user information ?
  if (fUserEventInformationFlag) {
    // the user info is deleted by the event destructor, so
    // we need to create a new one everytime
    l.fUserEventInformation = new GateUserEventInformation;
    l.fUserEventInformation->BeginOfEventAction(event);
    event->SetUserInformation(l.fUserEventInformation);
  }

  // prepare the next source
  PrepareNextSource();

  // check if this is not the end of the run
  CheckForNextRun();
}

void GateSourceManager::InitializeVisualization() {
  if (!fVisualizationFlag || (fVisualizationTypeFlag == "gdml") ||
      (fVisualizationTypeFlag == "gdml_file_only"))
    return;

  char *argv[1]; // ok on osx
  // char **argv = new char*[1]; // not ok on osx
  if (fVisualizationTypeFlag == "qt") {
    fUIEx = new G4UIExecutive(1, argv, fVisualizationTypeFlag);
    // fUIEx = new G4UIExecutive(1, argv, "qt"); // FIXME
    // FIXME does not always work on Linux ? only OSX for the moment
    fUIEx->SetVerbose(fVisualizationVerboseFlag);
  }

  auto *uim = G4UImanager::GetUIpointer();

  // Needed to remove verbose
  uim->SetCoutDestination(&fSilent);

  // Apply all visu commands
  for (const auto &x : fVisCommands) {
    uim->ApplyCommand(x);
  }

  // Verbose for visu
  /* quiet,       // Nothing is printed.
   startup,       // Startup messages are printed...
   errors,        // ...and errors...
   warnings,      // ...and warnings...
   confirmations, // ...and confirming messages...
   parameters,    // ...and parameters of scenes and views...
   all            // ...and everything available. */
  if (fVisualizationVerboseFlag)
    G4VisManager::GetInstance()->SetVerboseLevel("all");
  else
    G4VisManager::GetInstance()->SetVerboseLevel("quit");
}

void GateSourceManager::StartVisualization() const {
#ifdef USE_GDML
  if (fVisualizationTypeFlag == "gdml") {
    G4GDMLParser parser;
    parser.SetRegionExport(true);
    parser.Write(fVisualizationFile,
                 G4TransportationManager::GetTransportationManager()
                     ->GetNavigatorForTracking()
                     ->GetWorldVolume()
                     ->GetLogicalVolume());
  }
#else
  if (fVisualizationTypeFlag == "gdml") {
    std::cout << "Error: GDML is not activated with Geant4" << std::endl;
    return;
  }
#endif

  // if (!fVisualizationFlag || (fVisualizationTypeFlag == "vrml") ||
  //    (fVisualizationTypeFlag == "vrml_file_only") ||
  //    (fVisualizationTypeFlag == "gdml") ||
  //    (fVisualizationTypeFlag == "gdml_file_only"))
  //  return;
  if (fVisualizationFlag && fVisualizationTypeFlag == "qt") {
    fUIEx->SessionStart();
    delete fUIEx;
  }
}

bool GateSourceManager::IsEndOfSimulationForWorker() const {
  auto &l = fThreadLocalData.Get();
  return (l.fNextRunId >= fSimulationTimes.size());
}
