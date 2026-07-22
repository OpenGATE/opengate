/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#include "GateSourceManager.h"
#include "GateHelpers.h"
#include "GateHelpersDict.h"
#include "GateSignalHandler.h"
#if defined(_MSC_VER)
#pragma warning(push)
#pragma warning(disable : 4244 4267)
#endif
#include "indicators.hpp"
#if defined(_MSC_VER)
#pragma warning(pop)
#endif
#include <CLHEP/Units/SystemOfUnits.h>
#include <G4Exception.hh>
#include <G4MTRunManager.hh>
#include <G4RunManager.hh>
#include <G4TransportationManager.hh>
#include <G4UIExecutive.hh>
#include <G4UImanager.hh>
#include <G4UnitsTable.hh>
#include <cmath>
#include <iostream>
#include <limits>
#include <pybind11/numpy.h>

#ifdef USE_GDML
#include <G4GDMLParser.hh>
#endif

/* There will be one SourceManager per thread */

bool GateSourceManager::fRunTerminationFlag = false;
std::atomic<std::uint64_t> GateSourceManager::fGeneratedPrimariesThisRun{0};
std::atomic<bool> GateSourceManager::fPrimaryLimitWarningIssued{false};
std::uint64_t GateSourceManager::fMaxPrimariesPerRun = INT32_MAX;

GateSourceManager::GateSourceManager() {
  fUIEx = nullptr;
  fVisualizationVerboseFlag = false;
  fVisualizationFlag = false;
  fVisualizationType = "qt";
  fVisualizationFile = "g4writertest.gdml";
  fVerboseLevel = 0;
  fUserEventInformationFlag = false;
  fProgressBarFlag = false;
  fProgressReportInterval = 0.0;
  auto &l = fThreadLocalData.Get();
  l.fStartNewRun = true;
  l.fNextRunId = 0;
  l.fUserEventInformation = nullptr;
  l.fCurrentSimulationTime = 0;
  l.fNextActiveSource = nullptr;
  l.fNextSimulationTime = 0;
  l.fProgressBar = nullptr;
  fExpectedNumberOfEvents = 0;
  fProgressBarStep = 1000;
  fCurrentEvent = 0;
  fRunTerminationFlag = false;
}

GateSourceManager::~GateSourceManager() {
  // fUIEx is already deleted
}

void GateSourceManager::SetRunTerminationFlag(bool flag) {
  fRunTerminationFlag = flag;
}

std::uint64_t GateSourceManager::GetPlatformMaxPrimariesPerRun() {
  return std::numeric_limits<G4int>::max();
}

void GateSourceManager::SetMaxPrimariesPerRun(std::uint64_t value) {
  if (value == 0) {
    fMaxPrimariesPerRun = GetPlatformMaxPrimariesPerRun();
    return;
  }
  fMaxPrimariesPerRun = value;
}

void GateSourceManager::ResetPrimaryCounterForRun() {
  fGeneratedPrimariesThisRun.store(0, std::memory_order_relaxed);
  fPrimaryLimitWarningIssued.store(false, std::memory_order_relaxed);
}

bool GateSourceManager::TryReservePrimarySlot() {
  auto current = fGeneratedPrimariesThisRun.load(std::memory_order_relaxed);
  while (current < fMaxPrimariesPerRun) {
    if (fGeneratedPrimariesThisRun.compare_exchange_weak(
            current, current + 1, std::memory_order_relaxed,
            std::memory_order_relaxed)) {
      return true;
    }
  }
  return false;
}

void GateSourceManager::WarnPrimaryLimitReached() {
  bool warning_already_issued =
      fPrimaryLimitWarningIssued.exchange(true, std::memory_order_relaxed);
  if (warning_already_issued) {
    return;
  }

  G4ExceptionDescription ed;
  ed << "The current Geant4 BeamOn() call reached the maximum supported "
     << "number of primaries (" << fMaxPrimariesPerRun << "). "
     << "The run is being stopped before generating additional primaries.";
  G4Exception("GateSourceManager::GeneratePrimaries", "GateSourceManager0001",
              JustWarning, ed);
}

void GateSourceManager::Initialize(const TimeIntervals &simulation_times,
                                   py::dict &options) {
  fSimulationTimes = simulation_times;
  auto &l = fThreadLocalData.Get();
  l.fStartNewRun = true;
  l.fNextRunId = 0;
  fOptions = options;
  fVisualizationFlag = DictGetBool(options, "visu");
  fVisualizationVerboseFlag = DictGetBool(options, "visu_verbose");
  fVisualizationType = DictGetStr(options, "visu_type");
  fVisualizationFile = DictGetStr(options, "visu_filename");
  if (fVisualizationType == "vrml" || fVisualizationType == "vrml_file_only")
    fVisCommands = DictGetVecStr(options, "visu_commands_vrml");
  else if (fVisualizationType == "gdml" ||
           fVisualizationType == "gdml_file_only")
    fVisCommands = DictGetVecStr(options, "visu_commands_gdml");
  else
    fVisCommands = DictGetVecStr(options, "visu_commands");
  fVerboseLevel = DictGetInt(options, "running_verbose_level");
  fProgressBarFlag = DictGetBool(options, "progress_bar");
  if (options.contains("max_primaries_per_run")) {
    SetMaxPrimariesPerRun(DictGetInt(options, "max_primaries_per_run"));
  } else {
    SetMaxPrimariesPerRun(GetPlatformMaxPrimariesPerRun());
  }
  InstallSignalHandler();
  ComputeExpectedNumberOfEvents();
  InitializeProgressBar();

  // Fake init of the EventModulo (will be changed in StartMasterThread or by
  // the user) thanks to /run/eventModulo 50000 1
  if (G4Threading::IsMultithreadedApplication()) {
    // (static cast is REQUIRED)
    const auto mt =
        static_cast<G4MTRunManager *>(G4RunManager::GetRunManager());
    mt->SetEventModulo(-1);
  }
}

void GateSourceManager::AddSource(GateVSource *source) {
  fSources.push_back(source);
}

void GateSourceManager::SetActors(const std::vector<GateVActor *> &actors) {
  fActors = actors;
  for (const auto actor : actors) {
    actor->SetSourceManager(this);
  }
}

GateVSource *
GateSourceManager::FindSourceByName(const std::string &name) const {
  for (auto *source : fSources) {
    if (source->fName == name)
      return source;
  }
  std::ostringstream oss;
  oss << "Cannot find the source '" << name << "' in the source manager"
      << std::endl;
  Fatal(oss.str());
  return nullptr;
}

G4String GateSourceManager::GetActiveSourceName() {
  auto &l = fThreadLocalData.Get();
  if (l.fNextActiveSource != 0) {
    G4String name = l.fNextActiveSource->fName;
    return name;
  }
  return "None";
}

void GateSourceManager::SetActiveSourcebyName(G4String sourceName) {
  auto &l = fThreadLocalData.Get();
  auto *source = FindSourceByName(sourceName);
  l.fNextActiveSource = source;
}

void GateSourceManager::StartMasterThread() {
  // Create the main macro command
  // (only performed in the master thread)
  if (G4Threading::IsMultithreadedApplication()) {
    // (static is needed, dynamic_cast lead to seg fault)
    auto mt = static_cast<G4MTRunManager *>(G4RunManager::GetRunManager());
    if (mt->GetEventModulo() == -1) {
      mt->SetEventModulo(10000); // default value (not a big influence)
      // Much faster with mode 1 than with mode 0 (which is default)
      G4MTRunManager::SetSeedOncePerCommunication(1);
    }
  }

  std::ostringstream oss;
  oss << "/run/beamOn " << INT32_MAX;
  const std::string run = oss.str();
  // Loop on run
  auto &l = fThreadLocalData.Get();
  l.fStartNewRun = true;
  for (size_t run_id = 0; run_id < fSimulationTimes.size(); run_id++) {
    ResetPrimaryCounterForRun();
    // Start Begin Of Run for MasterThread
    // (both for multi-thread and mono-thread app)
    // The conventional (threaded) BeginOfRun will be called
    // for all threads by the Action loop
    for (const auto &actor : fActors) {
      actor->BeginOfRunActionMasterThread(static_cast<int>(run_id));
    }
    InitializeVisualization();
    auto *uim = G4UImanager::GetUIpointer();
    uim->ApplyCommand(run);

    for (const auto &actor : fActors) {
      int ret = actor->EndOfRunActionMasterThread(static_cast<int>(run_id));
    }
    StartVisualization();
  }

  // progress bar (only thread 0)
  if (fProgressBarFlag) {
    if (G4Threading::IsMultithreadedApplication() &&
        G4Threading::G4GetThreadId() != 0)
      return;
    // l.fProgressBar->mark_as_completed(); // seems to 'duplicate' progress bar
    show_console_cursor(true);
  }
}

void GateSourceManager::InitializeProgressBar() {
  if (!fProgressBarFlag)
    return;

  if (fExpectedNumberOfEvents <= 0) {
    ComputeExpectedNumberOfEvents();
  }

  fProgressBarStep = (long)round((double)fExpectedNumberOfEvents / 100.0);
  if (fExpectedNumberOfEvents > 1e7)
    fProgressBarStep = (long)round((double)fExpectedNumberOfEvents / 1000.0);
  if (fProgressBarStep < 1) {
    fProgressBarStep = 1;
  }

  // the progress bar is only for one thread (id ==0)
  if (G4Threading::IsMultithreadedApplication() &&
      G4Threading::G4GetThreadId() != 0)
    return;
  auto &l = fThreadLocalData.Get();
  l.fProgressBar = std::make_unique<ProgressBar>(
      option::BarWidth{50}, option::Start{""}, option::Fill{"■"},
      option::Lead{"■"}, option::End{""}, option::ShowElapsedTime{true},
      option::ShowRemainingTime{true},
      option::MaxProgress{fExpectedNumberOfEvents});
  // show_console_cursor(true);
  fCurrentEvent = 0;
}

void GateSourceManager::ComputeExpectedNumberOfEvents() {
  fExpectedNumberOfEvents = 0;
  for (auto *source : fSources) {
    fExpectedNumberOfEvents +=
        source->GetExpectedNumberOfEvents(fSimulationTimes);
  }
}

long int GateSourceManager::GetExpectedNumberOfEvents() const {
  return fExpectedNumberOfEvents;
}

unsigned long GateSourceManager::GetRunGeneratedEvents() const {
  unsigned long n = 0;
  for (const auto *source : fSources) {
    n += source->GetRunGeneratedEvents();
  }
  return n;
}

unsigned long GateSourceManager::GetTotalGeneratedEvents() const {
  unsigned long n = 0;
  for (const auto *source : fSources) {
    n += source->GetTotalGeneratedEvents();
  }
  return n;
}

double GateSourceManager::GetCurrentSimulationTime() const {
  auto &l = fThreadLocalData.Get();
  return l.fCurrentSimulationTime;
}

int GateSourceManager::GetCurrentRunId() const {
  auto &l = fThreadLocalData.Get();
  return l.fNextRunId;
}

void GateSourceManager::PrepareRunToStart(int run_id) {
  /*
    Start run run_id
    fCurrentTimeInterval = interval run_id
    fCurrentTime = start of interval run_id
    fNextTime = end of interval run_id
    fRunTerminationFlag = false
    Call PrepareNextRun on all sources
  */

  auto &l = fThreadLocalData.Get();
  l.fCurrentTimeInterval = fSimulationTimes[run_id];
  // set the current time
  l.fCurrentSimulationTime = l.fCurrentTimeInterval.first;
  // init the next time as the end of the interval by default
  l.fNextSimulationTime = l.fCurrentTimeInterval.second;
  // reset abort run flag to false
  fRunTerminationFlag = false;
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
  Log(LogLevel_RUN, fVerboseLevel, "Starting run {} ({})\n", run_id,
      G4Threading::IsMasterThread() == TRUE
          ? "master"
          : std::to_string(G4Threading::G4GetThreadId()));
}

void GateSourceManager::PrepareNextSource() const {
  auto &l = fThreadLocalData.Get();
  l.fNextActiveSource = nullptr;
  G4int nbOfRunFromTimes = static_cast<G4int>(fSimulationTimes.size());

  double min_time = l.fCurrentTimeInterval.first;
  double max_time = l.fCurrentTimeInterval.second;

  // Ask all sources their next time, keep the closest one
  for (auto *source : fSources) {
    unsigned long numberOfSimulatedEvents = source->GetRunGeneratedEvents();
    auto t = source->PrepareNextTime(l.fCurrentSimulationTime,
                                     numberOfSimulatedEvents);
    if ((t >= min_time) && (t < max_time)) {
      max_time = t;
      l.fNextActiveSource = source;
      l.fNextSimulationTime = t;
    }
  }

  // If no next time in the current interval, active source is NULL
}

void GateSourceManager::CheckForNextRun() const {
  auto &l = fThreadLocalData.Get();
  l.fStartNewRun = false;
  if (l.fNextActiveSource == nullptr || fRunTerminationFlag) {
    G4RunManager::GetRunManager()->AbortRun(true); // FIXME true or false ?
    l.fStartNewRun = true;
    l.fNextRunId++;
    if (l.fNextRunId >= fSimulationTimes.size()) {
      // Sometimes, the source must clean some data in its own thread, not by
      // the master thread (for example, with a G4SingleParticleSource object)
      // The CleanThread method is used for that.
      for (auto *source : fSources) {
        source->CleanWorkerThread();
      }
    }
  }
}

void GateSourceManager::SetProgressReportCallback(py::function func,
                                                  double interval_seconds) {
  fProgressReportCallback = func;
  fProgressReportInterval = interval_seconds / CLHEP::s;
  fLastProgressReportTime = std::chrono::steady_clock::now();
}

void GateSourceManager::CheckProgressReport() const {
  if (fProgressReportInterval <= 0.0 || !fProgressReportCallback) {
    return;
  }
  auto now = std::chrono::steady_clock::now();
  std::unique_lock<std::mutex> lock(fProgressReportMutex, std::try_to_lock);
  if (!lock.owns_lock()) {
    return;
  }
  double elapsed =
      std::chrono::duration<double>(now - fLastProgressReportTime).count();
  if (elapsed >= fProgressReportInterval) {
    fLastProgressReportTime = now;
    // gil is needed when using fProgressReportCallback
    py::gil_scoped_acquire acquire;
    try {
      fProgressReportCallback();
    } catch (const py::error_already_set &e) {
      std::cerr << "Error in progress report callback: " << e.what()
                << std::endl;
    }
  }
}

void GateSourceManager::GeneratePrimaries(G4Event *event) {
  CheckProgressReport();
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
    const auto *particle_def = particle_table->FindParticle("geantino");
    auto *particle = new G4PrimaryParticle(particle_def);
    const auto p = G4ThreeVector();
    auto *vertex = new G4PrimaryVertex(p, l.fCurrentSimulationTime);
    vertex->SetPrimary(particle);
    event->AddPrimaryVertex(vertex);
    // (allocated memory is leaked)
  } else {
    if (TryReservePrimarySlot()) {
      // shoot particle
      l.fNextActiveSource->GeneratePrimaries(event, l.fCurrentSimulationTime);
      // log (after particle creation)
      if (LogLevel_EVENT <= GateSourceManager::fVerboseLevel) {
        const auto *prim = event->GetPrimaryVertex(0)->GetPrimary(0);
        std::string t = G4BestUnit(l.fCurrentSimulationTime, "Time");
        std::string e = G4BestUnit(prim->GetKineticEnergy(), "Energy");
        std::string s = l.fNextActiveSource->fName;
        Log(LogLevel_EVENT, fVerboseLevel,
            "Event {} {} {} {} {:.2f} {:.2f} {:.2f} ({})\n",
            event->GetEventID(), t,
            prim->GetParticleDefinition()->GetParticleName(), e,
            event->GetPrimaryVertex(0)->GetPosition()[0],
            event->GetPrimaryVertex(0)->GetPosition()[1],
            event->GetPrimaryVertex(0)->GetPosition()[2], s);
      }
    } else {
      WarnPrimaryLimitReached();
      fRunTerminationFlag = true;

      auto *particle_table = G4ParticleTable::GetParticleTable();
      const auto *particle_def = particle_table->FindParticle("geantino");
      auto *particle = new G4PrimaryParticle(particle_def);
      const auto p = G4ThreeVector();
      auto *vertex = new G4PrimaryVertex(p, l.fCurrentSimulationTime);
      vertex->SetPrimary(particle);
      event->AddPrimaryVertex(vertex);
      // (allocated memory is leaked)
    }
  }

  // Add user information?
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

  // progress bar
  if (fProgressBarFlag) {
    // do nothing if not the first thread
    if (G4Threading::IsMultithreadedApplication() &&
        G4Threading::G4GetThreadId() != 0)
      return;
    // count the number of events already generated
    fCurrentEvent = fCurrentEvent + 1;
    // update the bar sometimes
    if (fCurrentEvent % fProgressBarStep == 0) {
      l.fProgressBar->set_progress(fCurrentEvent);
    }
  }
}

void GateSourceManager::InitializeVisualization() {
  if (!fVisualizationFlag || (fVisualizationType == "gdml") ||
      (fVisualizationType == "gdml_file_only"))
    return;

  if (fVisualizationFlag && (fVisualizationType == "qt")) {
#if USE_VISU == 0
    fVisualizationFlag = false;
    return;
#endif
  }

  static int argc = 1;
  static char *args[] = {(char *)"opengate", nullptr};
  static char **argv = args;
  argc = 1; // Reset argc in case it was modified in a previous call

  if (fVisualizationType == "qt") {
    fUIEx = new G4UIExecutive(1, argv, fVisualizationType);
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

  // Add the image to the g4_solids Need to be done after GL init
  /*#ifdef GATEIMAGEBOX_USE_OPENGL
    if (fVisualizationType == "qt") {
      for (auto *g4_solid : fImageBoxes) {
        g4_solid->InitialiseSlice();
      }
    }
  #endif*/
}

void GateSourceManager::RegisterImageBox(GateImageBox *g4_solid) {
  fImageBoxes.push_back(g4_solid);
}

void GateSourceManager::StartVisualization() const {
#ifdef USE_GDML
  if (fVisualizationType == "gdml") {
    G4GDMLParser parser;
    parser.SetRegionExport(true);
    parser.Write(fVisualizationFile,
                 G4TransportationManager::GetTransportationManager()
                     ->GetNavigatorForTracking()
                     ->GetWorldVolume()
                     ->GetLogicalVolume());
  }
#else
  if (fVisualizationType == "gdml") {
    std::cout << "Error: GDML is not activated with Geant4" << std::endl;
    return;
  }
#endif

  if (fVisualizationFlag) {
    for (auto &source : fSources) {
      source->Visualize();
    }
  }

  if (fVisualizationFlag && fVisualizationType == "qt") {
    fUIEx->SessionStart();
    delete fUIEx;
  }
}

bool GateSourceManager::IsEndOfSimulationForWorker() const {
  auto &l = fThreadLocalData.Get();
  return (l.fNextRunId >= fSimulationTimes.size());
}
