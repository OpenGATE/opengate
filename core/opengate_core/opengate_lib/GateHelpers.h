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

void Fatal(std::string s);

void FatalKeyError(std::string s);

#define DD(a) std::cout << #a << " = [ " << (a) << " ]\n";

// debug print
#define DDD(a)                                                                 \
  {                                                                            \
    std::cout << "OPENGATE [" << G4Threading::G4GetThreadId() << "] ("         \
              << __func__ << ") ==> " << #a << " = [ " << (a) << " ]\n";       \
  }

// for vector
#define DDDV(a)                                                                \
  {                                                                            \
    std::cout << "OPENGATE [" << G4Threading::G4GetThreadId() << "] ("         \
              << __func__ << ") ==> " << #a << " (" << (a).size() << ") = ";   \
    for (auto &_i : (a))                                                       \
      std::cout << _i << " ";                                                  \
    std::cout << "\n";                                                         \
  }

// debug for error
#define DDE(a)                                                                 \
  {                                                                            \
    std::cout << "OPENGATE ERROR [" << G4Threading::G4GetThreadId() << "] ("   \
              << __func__ << ") ==> " << #a << " = [ " << (a) << " ]\n";       \
  }

// Log verbose (with color and level)
template <typename S, typename... Args>
void Log(int level, const S &format_str, Args &&...args);

template <typename S, typename... Args>
void LogDebug(int level, const S &format_str, Args &&...args);

extern const int LogLevel_RUN;
extern const int LogLevel_EVENT;

// https://en.wikipedia.org/wiki/Full_width_at_half_maximum
// FWHM = 2.355 x sigma
static const double sigma_to_fwhm = 2.0 * sqrt(2.0 * log(2.0));
static const double fwhm_to_sigma = 1.0 / sigma_to_fwhm;

#include "GateHelpers.txx"

#endif // GateHelpers_h
