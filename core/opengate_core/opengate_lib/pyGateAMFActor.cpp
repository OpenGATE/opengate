/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#include <pybind11/pybind11.h>
#include <pybind11/stl.h>
#include <pybind11/numpy.h>

namespace py = pybind11;

#include "GateAMFActor.h"

class PyGateAMFActor : public GateAMFActor {
public:
  // Inherit the constructors
  using GateAMFActor::GateAMFActor;

  void BeginOfRunActionMasterThread(int run_id) override {
    PYBIND11_OVERLOAD(void, GateAMFActor, BeginOfRunActionMasterThread, run_id);
  }

  int EndOfRunActionMasterThread(int run_id) override {
    PYBIND11_OVERLOAD(int, GateAMFActor, EndOfRunActionMasterThread, run_id);
  }
};

void init_GateAMFActor(py::module &m) {
  py::class_<GateAMFActor, PyGateAMFActor,
             std::unique_ptr<GateAMFActor, py::nodelete>,
             GateVActor>(m, "GateAMFActor")
      .def(py::init<py::dict &>())
      .def("InitializeUserInfo", &GateAMFActor::InitializeUserInfo)
      .def("InitializeCpp", &GateAMFActor::InitializeCpp)
      .def("GetHistogramLabels", &GateAMFActor::GetHistogramLabels)
      .def("GetSpectraArray", [](const GateAMFActor &actor) {
        const auto image = actor.cpp_amf_microdosimetric_spectra;
        if (!image) throw std::runtime_error("AMF: spectra output is inactive");
        const auto size = image->GetLargestPossibleRegion().GetSize();
        py::array_t<double> data({static_cast<py::ssize_t>(size[2]),
                                static_cast<py::ssize_t>(size[1]),
                                static_cast<py::ssize_t>(size[0]),
                                static_cast<py::ssize_t>(400)});
        std::copy_n(image->GetBufferPointer(), data.size(), data.mutable_data());
        return data;
      })
      .def("BeginOfRunActionMasterThread",
           &GateAMFActor::BeginOfRunActionMasterThread)
      .def("EndOfRunActionMasterThread",
           &GateAMFActor::EndOfRunActionMasterThread)
      .def_readwrite("cpp_amf_dose_image", &GateAMFActor::cpp_amf_dose_image)
      .def_readwrite("cpp_amf_dose_averaged_lineal_energy_saturation_corrected",
                     &GateAMFActor::cpp_amf_dose_averaged_lineal_energy_saturation_corrected)
      .def_readwrite("cpp_amf_dose_averaged_lineal_energy",
                     &GateAMFActor::cpp_amf_dose_averaged_lineal_energy)
      .def_readwrite("cpp_amf_alpha_mcfmkm_image", &GateAMFActor::cpp_amf_alpha_mcfmkm_image)
      .def_readwrite("cpp_amf_beta_mcfmkm_image", &GateAMFActor::cpp_amf_beta_mcfmkm_image)
                     // // .def_readwrite("NbOfEvent", &GateAMFActor::NbOfEvent)
      .def("GetPhysicalVolumeName", &GateAMFActor::GetPhysicalVolumeName)
      .def("SetPhysicalVolumeName", &GateAMFActor::SetPhysicalVolumeName)
      .def_readwrite("NbOfEvent", &GateAMFActor::NbOfEvent)
      .def("GetMicrodosimetricSpectraFlag", &GateAMFActor::GetMicrodosimetricSpectraFlag)
      .def("SetMicrodosimetricSpectraFlag", &GateAMFActor::SetMicrodosimetricSpectraFlag)
      .def("GetDoseAveragedLinealEnergySaturationCorrectedFlag", &GateAMFActor::GetDoseAveragedLinealEnergySaturationCorrectedFlag)
      .def("SetDoseAveragedLinealEnergySaturationCorrectedFlag", &GateAMFActor::SetDoseAveragedLinealEnergySaturationCorrectedFlag)
      .def("GetDoseAveragedLinealEnergyFlag", &GateAMFActor::GetDoseAveragedLinealEnergyFlag)
      .def("SetDoseAveragedLinealEnergyFlag", &GateAMFActor::SetDoseAveragedLinealEnergyFlag)
      .def("SetAlphaMCFMKMFlag", &GateAMFActor::SetAlphaMCFMKMFlag)
      .def("SetBetaMCFMKMFlag", &GateAMFActor::SetBetaMCFMKMFlag)
      .def("SetDomainRadius", &GateAMFActor::SetDomainRadius)
      .def("SetBetaRef", &GateAMFActor::SetBetaRef)
      .def("SetAlphaRef", &GateAMFActor::SetAlphaRef)
      .def("SetAlphaNot", &GateAMFActor::SetAlphaNot)
      .def("SetNucleusRadius", &GateAMFActor::SetNucleusRadius)
       .def_readwrite("fPhysicalVolumeName",
       &GateAMFActor::fPhysicalVolumeName);

  // Internal numerical interface for focused scientific/edge-case tests.
  py::class_<MicrodosimetricCalculator>(m, "_AMFCalculator")
      .def(py::init<size_t, double, double, double, double, int, int>())
      .def("load", &MicrodosimetricCalculator::setTSEDfilename)
      .def("calculate", [](MicrodosimetricCalculator &calculator, double z,
                            double mass, double energy, double dedx, double dose) {
        GateAMFActor::VectorPixelType spectrum;
        double yd = 0, ys = 0;
        calculator.calculateDoseWeightedMicrodosimetricFunctionFast(
            spectrum, z, mass, energy, dedx, dose, yd, ys);
        py::array_t<double> values(spectrum.Size());
        std::copy_n(spectrum.GetDataPointer(), spectrum.Size(), values.mutable_data());
        return py::make_tuple(values, yd, ys);
      });
}
