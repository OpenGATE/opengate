/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#include "GamVFilter.h"

GamVFilter::GamVFilter() {

}

GamVFilter::~GamVFilter() {
}

void GamVFilter::Initialize(py::dict &) {

}

bool GamVFilter::Accept(const G4Run *) const {
    return true;

}

bool GamVFilter::Accept(const G4Event *) const {
    return true;
}

bool GamVFilter::Accept(const G4Track *) const {
    return true;
}

bool GamVFilter::Accept(const G4Step *) const {
    return true;
}