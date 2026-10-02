/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#include <pybind11/numpy.h>
#include <pybind11/pybind11.h>
#include <pybind11/stl.h>

namespace py = pybind11;

#include "GateAMFActor.h"

class PyGateAMFActor : public GateAMFActor {
public:
  // Inherit the constructors
  using GateAMFActor::GateAMFActor;

  /** Forward the master run start to a Python override when present. */
  void BeginOfRunActionMasterThread(int run_id) override {
    PYBIND11_OVERLOAD(void, GateAMFActor, BeginOfRunActionMasterThread, run_id);
  }

  /** Forward master finalization to Python so fetched images reach output
   * interfaces. */
  int EndOfRunActionMasterThread(int run_id) override {
    PYBIND11_OVERLOAD(int, GateAMFActor, EndOfRunActionMasterThread, run_id);
  }
};

/** Register actor methods and the internal numerical calculator with Python. */
void init_GateAMFActor(py::module &m) {
  // Internal access lets Python tests exercise the production reduction
  // directly, without a separate native executable or a reimplementation of its
  // rules.
  py::class_<AMFRawAccumulator>(m, "_AMFRawAccumulator")
      .def(py::init<size_t, const std::array<bool, 4> &, bool>(),
           "Allocate raw dose, enabled yD/yS/alpha/sqrt(beta) moments and "
           "optional spectra.")
      .def_readwrite("dose", &AMFRawAccumulator::dose)
      .def_readwrite("moments", &AMFRawAccumulator::moments)
      .def_readwrite("spectra", &AMFRawAccumulator::spectra)
      .def_readonly("finalized", &AMFRawAccumulator::finalized)
      .def_readonly("consumed", &AMFRawAccumulator::consumed)
      .def("merge", &AMFRawAccumulator::Merge,
           "Consume compatible raw state exactly once; reject finalized or "
           "self state.")
      .def("finalize", &AMFRawAccumulator::Finalize,
           "Normalize moments and spectra by dose, square mixed sqrt(beta), "
           "zero empty voxels.")
      .def("release", &AMFRawAccumulator::ReleaseBuffers,
           "Release buffers after consumption or finalization; reject active "
           "state.");

  py::class_<GateAMFActor, PyGateAMFActor,
             std::unique_ptr<GateAMFActor, py::nodelete>, GateVActor>(
      m, "GateAMFActor")
      .def(py::init<py::dict &>(),
           "Construct the C++ AMF actor from OpenGATE user information.")
      .def(
          "InitializeUserInfo", &GateAMFActor::InitializeUserInfo,
          "Read grid settings and load the AMF coefficients before allocation.")
      .def("InitializeCpp", &GateAMFActor::InitializeCpp,
           "Validate dimensions, allocate enabled images and freeze AMF "
           "configuration.")
      .def("GetHistogramLabels", &GateAMFActor::GetHistogramLabels,
           "Return 400 lineal-energy bin midpoints in keV/um.")
      .def(
          "GetSpectraArray",
          [](const GateAMFActor &actor) {
            const auto image = actor.cpp_amf_microdosimetric_spectra;
            if (!image)
              throw std::runtime_error("AMF: spectra output is inactive");
            const auto size = image->GetLargestPossibleRegion().GetSize();
            py::array_t<double> data({static_cast<py::ssize_t>(size[2]),
                                      static_cast<py::ssize_t>(size[1]),
                                      static_cast<py::ssize_t>(size[0]),
                                      static_cast<py::ssize_t>(400)});
            // Return an owning copy: Python data must survive release of actor
            // buffers.
            std::copy_n(image->GetBufferPointer(), data.size(),
                        data.mutable_data());
            return data;
          },
          "Copy the spectrum image to a float64 NumPy array ordered "
          "[z,y,x,400]; requires active spectra.")
      .def("BeginOfRunActionMasterThread",
           &GateAMFActor::BeginOfRunActionMasterThread,
           "Attach images and prepare the sole supported run (run_id=0).")
      .def("EndOfRunActionMasterThread",
           &GateAMFActor::EndOfRunActionMasterThread,
           "Merge finished workers, finalize images once and return zero.")
      .def_readwrite("cpp_amf_dose_image", &GateAMFActor::cpp_amf_dose_image)
      .def_readwrite(
          "cpp_amf_dose_averaged_lineal_energy_saturation_corrected",
          &GateAMFActor::
              cpp_amf_dose_averaged_lineal_energy_saturation_corrected)
      .def_readwrite("cpp_amf_dose_averaged_lineal_energy",
                     &GateAMFActor::cpp_amf_dose_averaged_lineal_energy)
      .def_readwrite("cpp_amf_alpha_mcfmkm_image",
                     &GateAMFActor::cpp_amf_alpha_mcfmkm_image)
      .def_readwrite("cpp_amf_beta_mcfmkm_image",
                     &GateAMFActor::cpp_amf_beta_mcfmkm_image)
      // // .def_readwrite("NbOfEvent", &GateAMFActor::NbOfEvent)
      .def(
          "GetPhysicalVolumeName", &GateAMFActor::GetPhysicalVolumeName,
          "Return the physical placement name used to attach the scoring grid.")
      .def("SetPhysicalVolumeName", &GateAMFActor::SetPhysicalVolumeName,
           "Set the physical placement name used to attach the scoring grid.")
      .def_readwrite("NbOfEvent", &GateAMFActor::NbOfEvent)
      .def("GetMicrodosimetricSpectraFlag",
           &GateAMFActor::GetMicrodosimetricSpectraFlag,
           "Return whether the 400-component spectrum output is enabled.")
      .def("SetMicrodosimetricSpectraFlag",
           &GateAMFActor::SetMicrodosimetricSpectraFlag,
           "Enable spectrum storage before initialization.")
      .def("GetDoseAveragedLinealEnergySaturationCorrectedFlag",
           &GateAMFActor::GetDoseAveragedLinealEnergySaturationCorrectedFlag,
           "Return whether saturation-corrected lineal energy is enabled.")
      .def("SetDoseAveragedLinealEnergySaturationCorrectedFlag",
           &GateAMFActor::SetDoseAveragedLinealEnergySaturationCorrectedFlag,
           "Enable saturation-corrected lineal energy before initialization.")
      .def("GetDoseAveragedLinealEnergyFlag",
           &GateAMFActor::GetDoseAveragedLinealEnergyFlag,
           "Return whether dose-mean lineal energy is enabled.")
      .def("SetDoseAveragedLinealEnergyFlag",
           &GateAMFActor::SetDoseAveragedLinealEnergyFlag,
           "Enable dose-mean lineal energy before initialization.")
      .def("SetAlphaMCFMKMFlag", &GateAMFActor::SetAlphaMCFMKMFlag,
           "Enable MCF MKM alpha scoring before initialization.")
      .def("SetBetaMCFMKMFlag", &GateAMFActor::SetBetaMCFMKMFlag,
           "Enable MCF MKM square-root beta scoring before initialization.")
      .def("SetDomainRadius", &GateAMFActor::SetDomainRadius,
           "Set the AMF target and biological domain radius in OpenGATE length "
           "units.")
      .def(
          "SetBetaRef", &GateAMFActor::SetBetaRef,
          "Set positive reference beta in OpenGATE inverse-dose-squared units.")
      .def(
          "SetAlphaRef", &GateAMFActor::SetAlphaRef,
          "Store reference alpha in inverse-dose units; unused by AMF scoring.")
      .def("SetAlphaNot", &GateAMFActor::SetAlphaNot,
           "Set nonnegative biological alpha0 in OpenGATE inverse-dose units.")
      .def("SetNucleusRadius", &GateAMFActor::SetNucleusRadius,
           "Set the biological nuclear radius in OpenGATE length units.")
      .def_readwrite("fPhysicalVolumeName", &GateAMFActor::fPhysicalVolumeName);

  // Internal numerical interface for focused scientific/edge-case tests.
  py::class_<MicrodosimetricCalculator>(m, "_AMFCalculator")
      .def(py::init<size_t, double, double, double, double, int, int>(),
           "Construct a 400-bin calculator: diameter/radii in um, beta in "
           "Gy^-2, iunit=2, columns=9.")
      .def("load", &MicrodosimetricCalculator::setTSEDfilename,
           "Load a tsed file containing exactly 576 rows of nine finite "
           "coefficients.")
      .def(
          "calculate",
          [](MicrodosimetricCalculator &calculator, double z, double mass,
             double energy, double dedx, double dose) {
            GateAMFActor::VectorPixelType spectrum;
            double yd = 0, ys = 0;
            calculator.calculateDoseWeightedMicrodosimetricFunctionFast(
                spectrum, z, mass, energy, dedx, dose, yd, ys);
            py::array_t<double> values(spectrum.Size());
            std::copy_n(spectrum.GetDataPointer(), spectrum.Size(),
                        values.mutable_data());
            return py::make_tuple(values, yd, ys);
          },
          "Return (dose*q(y), dose*yD, dose*yS) for Z, atomic mass, energy "
          "(MeV/u), DEDX (keV/um), dose (Gy).");
}
