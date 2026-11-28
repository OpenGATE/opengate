/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#include "GateImageMaskSolid.h"
#include <pybind11/numpy.h>
#include <pybind11/pybind11.h>
#include <pybind11/stl.h>

namespace py = pybind11;

namespace {

using ArrayD = py::array_t<double, py::array::c_style | py::array::forcecast>;

// the points (or directions) of an (N, 3) array
std::vector<G4ThreeVector> ToVectors(const ArrayD &a) {
  if (a.ndim() != 2 || a.shape(1) != 3)
    throw std::runtime_error("expected an array of shape (N, 3)");
  auto r = a.unchecked<2>();
  std::vector<G4ThreeVector> v(r.shape(0));
  for (py::ssize_t i = 0; i < r.shape(0); i++)
    v[i] = G4ThreeVector(r(i, 0), r(i, 1), r(i, 2));
  return v;
}

ArrayD FromVectors(const std::vector<G4ThreeVector> &v) {
  ArrayD a({py::ssize_t(v.size()), py::ssize_t(3)});
  auto w = a.mutable_unchecked<2>();
  for (std::size_t i = 0; i < v.size(); i++)
    for (int k = 0; k < 3; k++)
      w(i, k) = v[i][k];
  return a;
}

} // namespace

void init_GateImageMaskSolid(py::module &m) {

  py::class_<GateImageMaskSolid, G4VSolid,
             std::unique_ptr<GateImageMaskSolid, py::nodelete>>(
      m, "GateImageMaskSolid")
      .def(py::init(
          [](const std::string &name) { return new GateImageMaskSolid(name); }))
      .def("SetMask",
           [](GateImageMaskSolid &s, const std::array<int, 3> &size,
              const std::array<double, 3> &spacing,
              py::array_t<unsigned char,
                          py::array::c_style | py::array::forcecast>
                  mask,
              py::array_t<float, py::array::c_style | py::array::forcecast>
                  distance) {
             // numpy arrays in (z, y, x) order: the buffer is x fastest
             std::vector<unsigned char> m(mask.data(),
                                          mask.data() + mask.size());
             std::vector<float> d(distance.data(),
                                  distance.data() + distance.size());
             s.SetMask(size, spacing, m, d);
           })
      .def("IsVoxelInside", &GateImageMaskSolid::IsVoxelInside)
      .def("GetNumberOfInsideVoxels",
           &GateImageMaskSolid::GetNumberOfInsideVoxels)
      .def("GetNumberOfSurfaceFaces",
           &GateImageMaskSolid::GetNumberOfSurfaceFaces)
      // vectorised geometry queries, for the tests. Inside: 0 kOutside, 1
      // kSurface, 2 kInside (EInside)
      .def("inside",
           [](const GateImageMaskSolid &s, const ArrayD &points) {
             const auto p = ToVectors(points);
             py::array_t<int> r(py::ssize_t(p.size()));
             auto w = r.mutable_unchecked<1>();
             for (std::size_t i = 0; i < p.size(); i++)
               w(i) = int(s.Inside(p[i]));
             return r;
           })
      .def("surface_normal",
           [](const GateImageMaskSolid &s, const ArrayD &points) {
             const auto p = ToVectors(points);
             std::vector<G4ThreeVector> n(p.size());
             for (std::size_t i = 0; i < p.size(); i++)
               n[i] = s.SurfaceNormal(p[i]);
             return FromVectors(n);
           })
      .def("safety_to_in",
           [](const GateImageMaskSolid &s, const ArrayD &points) {
             const auto p = ToVectors(points);
             py::array_t<double> r(py::ssize_t(p.size()));
             auto w = r.mutable_unchecked<1>();
             for (std::size_t i = 0; i < p.size(); i++)
               w(i) = s.DistanceToIn(p[i]);
             return r;
           })
      .def("safety_to_out",
           [](const GateImageMaskSolid &s, const ArrayD &points) {
             const auto p = ToVectors(points);
             py::array_t<double> r(py::ssize_t(p.size()));
             auto w = r.mutable_unchecked<1>();
             for (std::size_t i = 0; i < p.size(); i++)
               w(i) = s.DistanceToOut(p[i]);
             return r;
           })
      .def("distance_to_in",
           [](const GateImageMaskSolid &s, const ArrayD &points,
              const ArrayD &directions) {
             const auto p = ToVectors(points);
             const auto v = ToVectors(directions);
             py::array_t<double> r(py::ssize_t(p.size()));
             auto w = r.mutable_unchecked<1>();
             for (std::size_t i = 0; i < p.size(); i++)
               w(i) = s.DistanceToIn(p[i], v[i]);
             return r;
           })
      .def("distance_to_out",
           [](const GateImageMaskSolid &s, const ArrayD &points,
              const ArrayD &directions) {
             const auto p = ToVectors(points);
             const auto v = ToVectors(directions);
             py::array_t<double> r(py::ssize_t(p.size()));
             auto w = r.mutable_unchecked<1>();
             std::vector<G4ThreeVector> n(p.size());
             for (std::size_t i = 0; i < p.size(); i++) {
               G4bool valid;
               w(i) = s.DistanceToOut(p[i], v[i], true, &valid, &n[i]);
             }
             return py::make_tuple(r, FromVectors(n));
           })
      .def("points_on_surface", [](const GateImageMaskSolid &s, int n) {
        std::vector<G4ThreeVector> p(n);
        for (int i = 0; i < n; i++)
          p[i] = s.GetPointOnSurface();
        return FromVectors(p);
      });
}
