/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */
#include <pybind11/pybind11.h>

namespace py = pybind11;

#include <streambuf>
#include "G4VSolid.hh"

void init_G4VSolid(py::module &m) {
    py::class_<G4VSolid,
        std::unique_ptr<G4VSolid, py::nodelete>>(m, "G4VSolid")

        .def("GetName", &G4VSolid::GetName)
        .def("SetName", &G4VSolid::SetName)
        .def("DumpInfo", &G4VSolid::DumpInfo)
        .def("StreamInfo", &G4VSolid::StreamInfo)

        .def("__str__", [](const G4VSolid &s) {
            std::ostringstream oss;
            s.StreamInfo(oss);
            return oss.str();
        })

            // FIXME add functions such as CalculateExtent BoundingLimits etc
        .def("BoundingLimits", &G4VSolid::BoundingLimits)
        .def("GetCubicVolume", &G4VSolid::GetCubicVolume)
        .def("GetSurfaceArea", &G4VSolid::GetSurfaceArea)
        .def("GetPointOnSurface", &G4VSolid::GetPointOnSurface);
}

