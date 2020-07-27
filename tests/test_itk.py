#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import gam
import itk

dim = 3
pixel_type = itk.ctype('float')
image_type = itk.Image[pixel_type, dim]
py_image = image_type.New()
region = itk.ImageRegion[dim]()
region.SetSize([100, 100, 100])
region.SetIndex([0,0,0])
py_image.SetRegions(region)
py_image.Allocate()  # needed !
py_image.FillBuffer(0)
print('allocate')
print(py_image)
#writerType = itk.ImageFileWriter[image_type]
#writer = writerType.New()
#writer.SetInput(py_image)
#writer.SetFileName('dose_before.mhd')
#writer.Update()
#print('write ok')

itk.imwrite(py_image, 'dose_before.mhd')
print('write ok')
