/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#ifndef GateHelpers_h
#define GateHelpers_h

#include "GateSourceManager.h"
#include <G4ThreeVector.hh>
#include <fmt/color.h>
#include <fmt/core.h>
#include <iostream>
#include <pybind11/stl.h>

namespace py = pybind11;

extern G4Mutex DebugMutex;

void Fatal(std::string s);

void FatalKeyError(std::string s);

#define DD(a) std::cout << #a << " = [ " << (a) << " ]\n";

// debug print
#define DDD(a)                                                                 \
  {                                                                            \
    G4AutoLock __l__(&DebugMutex);                                             \
    std::cout << "OPENGATE [" << G4Threading::G4GetThreadId() << "] ("         \
              << __func__ << ") ==> " << #a << " = [ " << (a) << " ]"          \
              << std::endl;                                                    \
  }

// for vector
#define DDDV(a)                                                                \
  {                                                                            \
    G4AutoLock l(&DebugMutex);                                                 \
    std::cout << "OPENGATE [" << G4Threading::G4GetThreadId() << "] ("         \
              << __func__ << ") ==> " << #a << " (" << (a).size() << ") = ";   \
    for (auto &_i : (a))                                                       \
      std::cout << _i << " ";                                                  \
    std::cout << std::endl;                                                    \
  }

// debug for error
#define DDE(a)                                                                 \
  {                                                                            \
    std::cout << "OPENGATE ERROR [" << G4Threading::G4GetThreadId() << "] ("   \
              << __func__ << ") ==> " << #a << " = [ " << (a) << " ]\n";       \
  }

// Log verbose (with color and level)
template <typename S, typename... Args>
void Log(int level, int verboseLevel, const S &format_str, Args &&...args);

template <typename S, typename... Args>
void LogDebug(const S &format_str, Args &&...args);

extern const int LogLevel_RUN;
extern const int LogLevel_EVENT;

// https://en.wikipedia.org/wiki/Full_width_at_half_maximum
// FWHM = 2.355 x sigma
static const double sigma_to_fwhm = 2.0 * sqrt(2.0 * log(2.0));
static const double fwhm_to_sigma = 1.0 / sigma_to_fwhm;

std::string DebugStep(const G4Step *step);

int createTestQtWindow();

#include "GateHelpers.txx"

#endif // GateHelpers_h
