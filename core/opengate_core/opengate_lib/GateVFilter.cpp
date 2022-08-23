/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#include "GateVFilter.h"

GateVFilter::GateVFilter() {}

GateVFilter::~GateVFilter() {}

void GateVFilter::Initialize(py::dict &) {}

bool GateVFilter::Accept(const G4Run *) const { return true; }

bool GateVFilter::Accept(const G4Event *) const { return true; }

bool GateVFilter::Accept(const G4Track *) const { return true; }

bool GateVFilter::Accept(const G4Step *) const { return true; }