/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#ifndef GamImageHelpers_h
#define GamImageHelpers_h

#include "GamHelpers.h"

template<class ImageType>
void ImageAddValue(typename ImageType::Pointer image,
                   typename ImageType::IndexType index,
                   typename ImageType::PixelType value) {
    //DDD(value);
    //DDD(index);
    auto v = image->GetPixel(index); // FIXME maybe 2 x FastComputeOffset can be spared
    image->SetPixel(index, v + value);
    //DDD(v + value);
}

#endif // GamImageHelpers_h

