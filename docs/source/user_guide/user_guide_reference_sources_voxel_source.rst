.. _source-voxel-source:

Voxelized source
================

Description
-----------

A voxelized source can be created as follows:

.. code:: python

   source = sim.add_source('VoxelSource', 'vox')
   source.particle = 'e-'
   source.activity = 4000 * Bq
   source.image = 'an_activity_image.mhd'
   source.direction.type = 'iso'
   source.energy.mono = 100 * keV
   source.attached_to = 'my_volume_name'

This code create a voxelized source. The 3D activity distribution is
read from the given image. This image is internally normalized such that
the sum of all pixels values is 1, leading to a 3D probability
distribution. Particles will be randomly located somewhere in the image
according to this probability distribution. Note that once an activity
voxel is chosen from this distribution, the location of the particle
inside the voxel is performed uniformly. In the given example, 4 kBq of
electrons of 140 keV will be generated.

Like all objects, by default, the source is located according to the
coordinate system of its attached_to volume. For example, if the attached_to
volume is a box, it will be the center of the box. If it is a voxelized
volume (typically a CT image), it will the **center** of this image: the
image own coordinate system (ITK’s origin) is not considered here. If
you want to align a voxelized activity with a CT image that have the
same coordinate system you should compute the correct translation. This
is done by the function
:func:`gate.image.get_translation_between_images_center`. See the contrib
example ``dose_rate.py``.

.. image:: ../figures/image_coord_system.png


Reference
---------

.. autofunction:: opengate.image.get_translation_between_images_center
.. autoclass :: opengate.sources.voxelsources.VoxelSource


