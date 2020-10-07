/* Copyright (C) 2020 Pablo Hernandez-Cerdan
 * This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at http://mozilla.org/MPL/2.0/. */

#ifndef DECLARE_ITK_IMAGE_PY_H
#define DECLARE_ITK_IMAGE_PY_H

#include <pybind11/pybind11.h>
#include <pybind11/functional.h>
#include <pybind11/stl_bind.h>
#include <pybind11/stl.h>
#include "pybind11/numpy.h"

#include "itkImage.h"
#include "itkSmartPointer.h"
#include "itkImportImageFilter.h"

/** For now make copies of data to numpy arrays.
 * Some examples (pybind11 source code docs are non-existant)
 * From: https://github.com/pybind/pybind11/issues/323
 * Also: https://github.com/pybind/pybind11/issues/1042
 * dtypes: https://docs.scipy.org/doc/numpy/user/basics.types.html
 * py::dtype::of<TIMG::ObjectType::PixelType>(),
 */
template<typename T>
inline auto np_array_ptr_after_check_dim_and_shape(
    pybind11::array_t<T, pybind11::array::c_style | pybind11::array::forcecast> np_array,
    const size_t img_dimension = 3) {
    auto buf = np_array.request();
    if (buf.ndim != 1) {
        throw std::runtime_error(
            "Input array must be 1D. "
            "But has dimension: " + std::to_string(buf.ndim));
    }
    if ((unsigned long) buf.shape[0] != img_dimension) {
        throw std::runtime_error(
            "Shape should be equal to ImageDimension but shape = " +
            std::to_string(buf.shape[0]) + " ].");
    }
    return buf.ptr;
};

template<typename TImagePointer>
inline void set_region(
    TImagePointer &img,
    pybind11::array_t<int,
        pybind11::array::c_style | pybind11::array::forcecast> index,
    pybind11::array_t<int,
        pybind11::array::c_style | pybind11::array::forcecast> size
) {
    using RegionType = typename TImagePointer::ObjectType::RegionType;
    typename RegionType::IndexType itk_index;
    const auto *data_index = static_cast<int *>(
        np_array_ptr_after_check_dim_and_shape<int>(index));
    itk_index[0] = data_index[0];
    itk_index[1] = data_index[1];
    itk_index[2] = data_index[2];
    typename RegionType::SizeType itk_size;
    const auto *data_size = static_cast<int *>(
        np_array_ptr_after_check_dim_and_shape<int>(size));
    if (data_size[0] < 0 || data_size[1] < 0 || data_size[2] < 0) {
        throw std::runtime_error(
            "In set_regions, input size cannot be negative.");
    }
    itk_size[0] = data_size[0];
    itk_size[1] = data_size[1];
    itk_size[2] = data_size[2];
    RegionType itk_region(itk_index, itk_size);
    img->SetRegions(itk_region);
    img->Allocate();
};

template<typename TImagePointer>
void declare_itk_image_ptr(pybind11::module &m, const std::string &typestr) {
    namespace py = pybind11;
    // const std::string pyclass_name = std::string("itk_") + typestr;
    py::class_<TImagePointer>(m, typestr.c_str())
        .def(py::init([]() {
                          return TImagePointer::ObjectType::New();
                      }
        ))
        .def("dimension", [](const TImagePointer &img) {
            return img->ImageDimension;
        })
        .def("index", [](const TImagePointer &img) {
            return py::array(
                img->ImageDimension, // shape
                img->GetLargestPossibleRegion().GetIndex().data());
        })
        .def("size", [](const TImagePointer &img) {
            return py::array(
                img->ImageDimension, // shape
                img->GetLargestPossibleRegion().GetSize().data());
        })
        .def("set_size", [](TImagePointer &img,
                            py::array_t<int, py::array::c_style | py::array::forcecast> size) {
                 py::array_t<int,
                     py::array::c_style | py::array::forcecast> zero_index(3);
                 return set_region(img, zero_index, size);
             }
        )
        .def("set_region", [](TImagePointer &img,
                              py::array_t<int, py::array::c_style | py::array::forcecast> index,
                              py::array_t<int, py::array::c_style | py::array::forcecast> size
             ) {
                 return set_region<TImagePointer>(img, index, size);
             },
             py::arg("index"),
             py::arg("size")
        )
        .def("spacing", [](const TImagePointer &img) {
            return py::array(
                img->ImageDimension, // shape
                img->GetSpacing().GetDataPointer());
        })
        .def("set_spacing", [](TImagePointer &img,
                               py::array_t<double, py::array::c_style | py::array::forcecast> spacing) {
                 const auto *data =
                     static_cast<double *>(
                         np_array_ptr_after_check_dim_and_shape<double>(spacing));
                 img->SetSpacing(data);
             }
        )
        .def("origin", [](const TImagePointer &img) {
            return py::array(
                img->ImageDimension, // shape
                img->GetOrigin().GetDataPointer());
        })
        .def("set_origin", [](TImagePointer &img,
                              py::array_t<double, py::array::c_style | py::array::forcecast> origin) {
                 const auto *data =
                     static_cast<double *>(
                         np_array_ptr_after_check_dim_and_shape<double>(origin));
                 img->SetOrigin(data);
             }
        )
        .def("direction", [](const TImagePointer &img) {
            const std::vector<size_t> shape{
                img->ImageDimension, img->ImageDimension};
            return py::array(
                shape,
                img->GetDirection().GetVnlMatrix().data_block());
        })
        .def("set_direction", [](TImagePointer &img,
                                 py::array_t<double, py::array::c_style | py::array::forcecast> direction) {
            // check dimensions (Dimension x Dimension)
            auto buf = direction.request();
            if (buf.ndim != 2) {
                throw std::runtime_error(
                    "Number of dimensions must be 2 (square matrix). "
                    "But it is: " + std::to_string(buf.ndim));
            }
            if (buf.shape[0] != img->ImageDimension ||
                buf.shape[1] != img->ImageDimension) {
                throw std::runtime_error(
                    "Shape should be Dimension x Dimension, but shape = [ " +
                    std::to_string(buf.shape[0]) + ", " +
                    std::to_string(buf.shape[1]) + " ].");
            }
            auto vnl_matrix = img->GetDirection().GetVnlMatrix();
            vnl_matrix.copy_in(direction.data());
            typename TImagePointer::ObjectType::DirectionType itk_direction(vnl_matrix);
            img->SetDirection(itk_direction);
        })
            // Follow numpy: CONTIG can be 'C' or 'F'
            // numpy default is F <- this is a pain coming from C data.
            // python ecosystem assume a F layout, so we return it as the default.
        .def("to_pyarray", [](const TImagePointer &img,
                              const std::string &contiguous) {
                 const auto size = img->GetLargestPossibleRegion().GetSize();
                 const auto shape = (contiguous == "F") ?
                                    std::vector<size_t>{size[2], size[1], size[0]} :
                                    std::vector<size_t>{size[0], size[1], size[2]};
                 return py::array(
                     py::dtype::of<typename TImagePointer::ObjectType::PixelType>(),
                     shape,
                     img->GetBufferPointer()
                 );
             },
             py::arg("contig") = "F")
            // TODO: Create a view (non-copy) of the data
            // Problems will arise with the contig differences between numpy(fortran) and c.
        .def("as_pyarray", [](const TImagePointer & /* img */,
                              const std::string & /* contiguous */) {
                 throw std::runtime_error("not implemented, use to_pyarray");
             },
             py::arg("contig") = "F")

        .def("from_pyarray", [](TImagePointer &img,
                                py::array_t<typename TImagePointer::ObjectType::PixelType> np_array,
                                const std::string &contiguous) {
                 using PixelType = typename TImagePointer::ObjectType::PixelType;
                 using Image = typename TImagePointer::ObjectType;
                 using ImporterType = itk::ImportImageFilter<PixelType, Image::ImageDimension>;
                 auto info = np_array.request();

                 auto importer = ImporterType::New();
                 auto region = img->GetLargestPossibleRegion();
                 auto size = region.GetSize();

                 if (contiguous == "F") {
                     std::copy(info.shape.rbegin(), info.shape.rend(), size.begin());
                 } else if (contiguous == "C") {
                     std::copy(info.shape.begin(), info.shape.end(), size.begin());
                 } else {
                     throw std::runtime_error(
                         "Unknown parameter contig: " + contiguous + ". Valid: F or C.");
                 }
                 region.SetSize(size);
                 // Note that region index is kept from the staring img.
                 importer->SetRegion(region);
                 // Metadata is ignored (defaulted)
                 // --> [DS] CHANGED. metadata is now imported
                 importer->SetOrigin(img->GetOrigin());
                 importer->SetSpacing(img->GetSpacing());
                 importer->SetDirection(img->GetDirection());
                 // img owns the buffer, not the import filter
                 const bool importImageFilterWillOwnTheBuffer = false;
                 const auto data = static_cast<typename TImagePointer::ObjectType::PixelType *>(info.ptr);
                 const auto numberOfPixels = np_array.size();
                 importer->SetImportPointer(
                     data, numberOfPixels, importImageFilterWillOwnTheBuffer);
                 importer->Update();
                 img = importer->GetOutput();
             },
             py::arg("input"),
             py::arg("contig") = "F"
        )

        .def("__repr__", [](const TImagePointer &img) {
            std::stringstream os;
            os << "Dimension: " << img->ImageDimension << std::endl;
            os << "LargestPossibleRegion: " << std::endl;
            os << "  Index: " << img->GetLargestPossibleRegion().GetIndex() << std::endl;
            os << "  Size (i,j,k) (c_array): " << img->GetLargestPossibleRegion().GetSize() << std::endl;
            os << "Origin: " << img->GetOrigin() << std::endl;
            os << "Spacing: " << img->GetSpacing() << std::endl;
            os << "Direction: " << std::endl;
            os << img->GetDirection();
            os << "Buffer: " << std::endl;
            img->GetPixelContainer()->Print(os);
            return os.str();
        });
}

#endif