#include "GateFilterData.h"
#include <pybind11/pybind11.h>
#include <pybind11/pytypes.h>

namespace py = pybind11;

void init_GateFilterData(py::module &m) {
  m
      // Energy
      .def("GetAttrTotalEnergyDeposit", &GetAttr<attr::TotalEnergyDeposit>::get)
      .def("GetAttrPostKineticEnergy", &GetAttr<attr::PostKineticEnergy>::get)
      .def("GetAttrPreKineticEnergy", &GetAttr<attr::PreKineticEnergy>::get)
      .def("GetAttrKineticEnergy", &GetAttr<attr::KineticEnergy>::get)
      .def("GetAttrTrackVertexKineticEnergy",
           &GetAttr<attr::TrackVertexKineticEnergy>::get)
      .def("GetAttrEventKineticEnergy", &GetAttr<attr::EventKineticEnergy>::get)

      // Time
      .def("GetAttrLocalTime", &GetAttr<attr::LocalTime>::get)
      .def("GetAttrGlobalTime", &GetAttr<attr::GlobalTime>::get)
      .def("GetAttrPreGlobalTime", &GetAttr<attr::PreGlobalTime>::get)
      .def("GetAttrTimeFromBeginOfEvent",
           &GetAttr<attr::TimeFromBeginOfEvent>::get)
      .def("GetAttrTrackProperTime", &GetAttr<attr::TrackProperTime>::get)

      // Misc
      .def("GetAttrWeight", &GetAttr<attr::Weight>::get)
      .def("GetAttrTrackID", &GetAttr<attr::TrackID>::get)
      .def("GetAttrParentID", &GetAttr<attr::ParentID>::get)
      .def("GetAttrEventID", &GetAttr<attr::EventID>::get)
      .def("GetAttrRunID", &GetAttr<attr::RunID>::get)
      .def("GetAttrThreadID", &GetAttr<attr::ThreadID>::get)
      .def("GetAttrTrackCreatorProcess",
           &GetAttr<attr::TrackCreatorProcess>::get)
      .def("GetAttrTrackCreatorModelName",
           &GetAttr<attr::TrackCreatorModelName>::get)
      .def("GetAttrTrackCreatorModelIndex",
           &GetAttr<attr::TrackCreatorModelIndex>::get)
      .def("GetAttrProcessDefinedStep", &GetAttr<attr::ProcessDefinedStep>::get)
      .def("GetAttrParticleName", &GetAttr<attr::ParticleName>::get)
      .def("GetAttrParentParticleName", &GetAttr<attr::ParentParticleName>::get)
      .def("GetAttrParticleType", &GetAttr<attr::ParticleType>::get)
      .def("GetAttrTrackVolumeName", &GetAttr<attr::TrackVolumeName>::get)
      .def("GetAttrTrackVolumeCopyNo", &GetAttr<attr::TrackVolumeCopyNo>::get)
      .def("GetAttrPreStepVolumeCopyNo",
           &GetAttr<attr::PreStepVolumeCopyNo>::get)
      .def("GetAttrPostStepVolumeCopyNo",
           &GetAttr<attr::PostStepVolumeCopyNo>::get)
      .def("GetAttrTrackVolumeInstanceID",
           &GetAttr<attr::TrackVolumeInstanceID>::get)
      .def("GetAttrPreStepUniqueVolumeID",
           &GetAttr<attr::PreStepUniqueVolumeID>::get)
      .def("GetAttrPostStepUniqueVolumeID",
           &GetAttr<attr::PostStepUniqueVolumeID>::get)
      .def("GetAttrPDGCode", &GetAttr<attr::PDGCode>::get)
      .def("GetAttrHitUniqueVolumeID", &GetAttr<attr::HitUniqueVolumeID>::get)

      // Position
      .def("GetAttrPosition", &GetAttr<attr::Position>::get)
      .def("GetAttrPostPosition", &GetAttr<attr::PostPosition>::get)
      .def("GetAttrPrePosition", &GetAttr<attr::PrePosition>::get)
      .def("GetAttrPrePositionLocal", &GetAttr<attr::PrePositionLocal>::get)
      .def("GetAttrPostPositionLocal", &GetAttr<attr::PostPositionLocal>::get)
      .def("GetAttrEventPosition", &GetAttr<attr::EventPosition>::get)
      .def("GetAttrTrackVertexPosition",
           &GetAttr<attr::TrackVertexPosition>::get)

      // Direction
      .def("GetAttrDirection", &GetAttr<attr::Direction>::get)
      .def("GetAttrPostDirection", &GetAttr<attr::PostDirection>::get)
      .def("GetAttrPreDirection", &GetAttr<attr::PreDirection>::get)
      .def("GetAttrPreDirectionLocal", &GetAttr<attr::PreDirectionLocal>::get)
      .def("GetAttrTrackVertexMomentumDirection",
           &GetAttr<attr::TrackVertexMomentumDirection>::get)
      .def("GetAttrEventDirection", &GetAttr<attr::EventDirection>::get)

      // Polarization
      .def("GetAttrPolarization", &GetAttr<attr::Polarization>::get)

      // Length
      .def("GetAttrStepLength", &GetAttr<attr::StepLength>::get)
      .def("GetAttrTrackLength", &GetAttr<attr::TrackLength>::get)

      // Scatter information
      .def("GetAttrUnscatteredPrimaryFlag",
           &GetAttr<attr::UnscatteredPrimaryFlag>::get);
}
