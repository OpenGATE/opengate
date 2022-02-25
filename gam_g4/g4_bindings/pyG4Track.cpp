/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */
#include <pybind11/pybind11.h>

namespace py = pybind11;

#include "G4Track.hh"

void init_G4Track(py::module &m) {

    py::class_<G4Track>(m, "G4Track")
        .def(py::init())
        .def("GetTrackID", &G4Track::GetTrackID)
        .def("GetVolume", &G4Track::GetVolume, py::return_value_policy::copy) // FIXME reference ?
        .def("GetParticleDefinition", &G4Track::GetParticleDefinition, py::return_value_policy::reference)

        /*
         TODO

         GetTrackID
         GetParentID
         GetDynamicParticle
         GetPosition
         GetGlobalTime
         GetLocalTime
         GetProperTime
         GetNextVolume


         */

        ;
}

