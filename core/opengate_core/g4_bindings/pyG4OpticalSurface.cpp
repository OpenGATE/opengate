#include "G4MaterialPropertiesTable.hh"
#include "G4OpticalSurface.hh"
#include "G4SurfaceProperty.hh"
#include <pybind11/pybind11.h>
#include <pybind11/stl.h>

namespace py = pybind11;

void init_G4OpticalSurface(py::module &m) {

  // Binding for G4OpticalSurfaceModel enumeration
  py::enum_<G4OpticalSurfaceModel>(m, "G4OpticalSurfaceModel")
      .value("glisur", G4OpticalSurfaceModel::glisur)
      .value("unified", G4OpticalSurfaceModel::unified)
      .value("LUT", G4OpticalSurfaceModel::LUT)
      .value("DAVIS", G4OpticalSurfaceModel::DAVIS)
      .value("dichroic", G4OpticalSurfaceModel::dichroic)
      .export_values();

  // Binding for G4OpticalSurfaceFinish enumeration
  py::enum_<G4OpticalSurfaceFinish>(m, "G4OpticalSurfaceFinish")
      .value("polished", G4OpticalSurfaceFinish::polished)
      .value("polishedfrontpainted",
             G4OpticalSurfaceFinish::polishedfrontpainted)
      .value("polishedbackpainted", G4OpticalSurfaceFinish::polishedbackpainted)
      .value("ground", G4OpticalSurfaceFinish::ground)
      .value("groundfrontpainted", G4OpticalSurfaceFinish::groundfrontpainted)
      .value("groundbackpainted", G4OpticalSurfaceFinish::groundbackpainted)
      .value("polishedlumirrorair", G4OpticalSurfaceFinish::polishedlumirrorair)
      .value("polishedlumirrorglue",
             G4OpticalSurfaceFinish::polishedlumirrorglue)
      .value("polishedair", G4OpticalSurfaceFinish::polishedair)
      .value("polishedteflonair", G4OpticalSurfaceFinish::polishedteflonair)
      .value("polishedtioair", G4OpticalSurfaceFinish::polishedtioair)
      .value("polishedtyvekair", G4OpticalSurfaceFinish::polishedtyvekair)
      .value("polishedvm2000air", G4OpticalSurfaceFinish::polishedvm2000air)
      .value("polishedvm2000glue", G4OpticalSurfaceFinish::polishedvm2000glue)
      .value("etchedlumirrorair", G4OpticalSurfaceFinish::etchedlumirrorair)
      .value("etchedlumirrorglue", G4OpticalSurfaceFinish::etchedlumirrorglue)
      .value("etchedair", G4OpticalSurfaceFinish::etchedair)
      .value("etchedteflonair", G4OpticalSurfaceFinish::etchedteflonair)
      .value("etchedtioair", G4OpticalSurfaceFinish::etchedtioair)
      .value("etchedtyvekair", G4OpticalSurfaceFinish::etchedtyvekair)
      .value("etchedvm2000air", G4OpticalSurfaceFinish::etchedvm2000air)
      .value("etchedvm2000glue", G4OpticalSurfaceFinish::etchedvm2000glue)
      .value("groundlumirrorair", G4OpticalSurfaceFinish::groundlumirrorair)
      .value("groundlumirrorglue", G4OpticalSurfaceFinish::groundlumirrorglue)
      .value("groundair", G4OpticalSurfaceFinish::groundair)
      .value("groundteflonair", G4OpticalSurfaceFinish::groundteflonair)
      .value("groundtioair", G4OpticalSurfaceFinish::groundtioair)
      .value("groundtyvekair", G4OpticalSurfaceFinish::groundtyvekair)
      .value("groundvm2000air", G4OpticalSurfaceFinish::groundvm2000air)
      .value("groundvm2000glue", G4OpticalSurfaceFinish::groundvm2000glue)
      .value("Rough_LUT", G4OpticalSurfaceFinish::Rough_LUT)
      .value("RoughTeflon_LUT", G4OpticalSurfaceFinish::RoughTeflon_LUT)
      .value("RoughESR_LUT", G4OpticalSurfaceFinish::RoughESR_LUT)
      .value("RoughESRGrease_LUT", G4OpticalSurfaceFinish::RoughESRGrease_LUT)
      .value("Polished_LUT", G4OpticalSurfaceFinish::Polished_LUT)
      .value("PolishedTeflon_LUT", G4OpticalSurfaceFinish::PolishedTeflon_LUT)
      .value("PolishedESR_LUT", G4OpticalSurfaceFinish::PolishedESR_LUT)
      .value("PolishedESRGrease_LUT",
             G4OpticalSurfaceFinish::PolishedESRGrease_LUT)
      .value("Detector_LUT", G4OpticalSurfaceFinish::Detector_LUT)
      .export_values();

  // Binding for G4SurfaceType enumeration
  py::enum_<G4SurfaceType>(m, "G4SurfaceType")
      .value("dielectric_metal", G4SurfaceType::dielectric_metal)
      .value("dielectric_dielectric", G4SurfaceType::dielectric_dielectric)
      .value("dielectric_LUT", G4SurfaceType::dielectric_LUT)
      .value("dielectric_LUTDAVIS", G4SurfaceType::dielectric_LUTDAVIS)
      .value("dielectric_dichroic", G4SurfaceType::dielectric_dichroic)
      .value("firsov", G4SurfaceType::firsov)
      .value("x_ray", G4SurfaceType::x_ray)
      .value("coated", G4SurfaceType::coated)
      .export_values();

  py::class_<G4SurfaceProperty>(m, "G4SurfaceProperty");

  py::class_<G4OpticalSurface, G4SurfaceProperty,
             std::unique_ptr<G4OpticalSurface, py::nodelete>>(
      m, "G4OpticalSurface")

      .def(py::init<const G4String &, G4OpticalSurfaceModel,
                    G4OpticalSurfaceFinish, G4SurfaceType, G4double>(),
           py::arg("name"), py::arg("model") = glisur,
           py::arg("finish") = polished,
           py::arg("type") = dielectric_dielectric, py::arg("value") = 1.0)

      .def("SetModel", &G4OpticalSurface::SetModel,
           py::return_value_policy::reference_internal)

      .def("GetModel", &G4OpticalSurface::GetModel)

      .def("SetType", &G4OpticalSurface::SetType,
           py::return_value_policy::reference_internal)

      .def("SetFinish", &G4OpticalSurface::SetFinish,
           py::return_value_policy::reference_internal)

      .def("SetSigmaAlpha", &G4OpticalSurface::SetSigmaAlpha,
           py::return_value_policy::reference_internal)

      .def("SetMaterialPropertiesTable",
           &G4OpticalSurface::SetMaterialPropertiesTable,
           py::return_value_policy::reference_internal)

      .def("DumpInfo", &G4OpticalSurface::DumpInfo);
}
