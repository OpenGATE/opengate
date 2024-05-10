#include <pybind11/pybind11.h>
#include <pybind11/stl.h>

namespace py = pybind11;

#include "G4LogicalBorderSurface.hh"
#include "G4OpticalSurface.hh"
#include "G4PVPlacement.hh"
#include "G4String.hh"
#include "G4SurfaceProperty.hh"
#include "G4VPhysicalVolume.hh"

void init_G4LogicalBorderSurface(py::module &m) {

  // Bind the base classes
  // py::class_<G4VPhysicalVolume>(m, "G4VPhysicalVolume");
  // py::class_<G4SurfaceProperty>(m, "G4SurfaceProperty");

  // Bind the subclasses, indicating their inheritance
  // py::class_<G4PVPlacement, G4VPhysicalVolume>(m, "G4PVPlacement");
  // py::class_<G4OpticalSurface, G4SurfaceProperty>(m, "G4OpticalSurface");

  py::class_<G4LogicalBorderSurface,
             std::unique_ptr<G4LogicalBorderSurface, py::nodelete>>(
      m, "G4LogicalBorderSurface")
      .def(py::init<const G4String &, G4VPhysicalVolume *, G4VPhysicalVolume *,
                    G4SurfaceProperty *>())
      .def("DumpInfo", &G4LogicalBorderSurface::DumpInfo);
}
