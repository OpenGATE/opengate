/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#include "GateHelpers.h"
#include <G4Threading.hh>
#include <stdexcept>

const int LogLevel_RUN = 20;
const int LogLevel_EVENT = 50;

void Fatal(std::string s) {
  std::cout << "ERROR in OPENGATE " << s << std::endl;
  exit(-1);
}

void FatalKeyError(std::string s) {
  throw py::key_error("Error in the Opengate library (C++): " + s);
}

// implement a thread-safe incremental addition for atomic doubles
// memory order is taking from comment in the code example on:
// https://en.cppreference.com/w/cpp/atomic/atomic/compare_exchange
void atomic_add_double(std::atomic<double> &ad, double const d) {
  double old;
  double new_val;
  //  int i = 0;
  do {
    old = ad;
    new_val = old + d;
    //    i++;
  } while (!ad.compare_exchange_weak(old, new_val));
  //  std::cout << i << std::endl;
}

// same as above, but returns the number of repeated attempts
int atomic_add_double_return_reattempts(std::atomic<double> &ad,
                                        double const d) {
  double old;
  double new_val;
  int i = 0;
  do {
    old = ad;
    new_val = old + d;
    i++;
  } while (!ad.compare_exchange_weak(old, new_val));
  return i - 1;
}
