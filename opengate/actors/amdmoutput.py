"""AMDM raw accumulators and derived images, using the actor-output lifecycle."""

from pathlib import Path

import itk
import numpy as np

from ..base import process_cls
from .actoroutput import ActorOutputImage
from .dataitems import (
    DataItemContainer,
    ImageDataItemContainerMixin,
    ItkImageDataItem,
    derived_data_item,
    _process_data_item_container_class,
)


class AMDMImageContainer(ImageDataItemContainerMixin, DataItemContainer):
    """Store raw 3D/4D sums and expose normalized images without changing them."""

    # Persist and merge only raw sums. Derived views never mutate those sums.
    _data_item_classes = (ItkImageDataItem,) * 3
    primary_item_identifiers = (0, 1, 2)  # restricted MeV, raw delta, raw gamma

    def _ratio(self, numerator, denominator):
        """Return a scalar double ratio image, using zero for zero denominators.

        Parameters are primary item identifiers. A 3D denominator broadcasts
        over the numerator's leading bin axis; metadata follows the numerator.
        Missing input data produces an empty data item.
        """
        n = self.data[numerator]
        d = self.data[denominator]
        if n.data_is_none or d.data_is_none:
            return ItkImageDataItem(data=None)
        na = itk.array_view_from_image(n.data)
        da = itk.array_view_from_image(d.data)
        # Arrays use [bin, z, y, x], so restricted energy broadcasts over bins.
        # Initialize the masked divisions to zero instead of inheriting NaNs.
        result = np.zeros_like(na)
        np.divide(na, da, out=result, where=da != 0)
        image = itk.image_from_array(result, is_vector=False)
        image.CopyInformation(n.data)
        item = ItkImageDataItem(data=image)
        item.number_of_samples = n.number_of_samples
        return item

    @derived_data_item(depends_on=(0, 1))
    def delta(self):
        """Return dimensionless bin fractions: raw delta / restricted energy."""
        return self._ratio(1, 0)

    @derived_data_item(depends_on=(1, 2))
    def gamma(self):
        """Return bin dose-mean lineal energies: raw gamma / raw delta, in keV/µm."""
        return self._ratio(2, 1)

    def set_image_properties(self, item="all", **properties):
        """Apply image properties to selected items, retaining the bin axis.

        Expand spatial origin/spacing to 4D with bin origin 0 and spacing 1;
        the existing image-item method handles spatial direction expansion.
        """
        # VoxelDepositActor supplies spatial properties. Keep the bin axis
        # independent when applying them to the two four-dimensional buffers.
        for image_item in self._get_image_data_items(item):
            p = dict(properties)
            if not image_item.data_is_none and image_item.data.GetImageDimension() == 4:
                for key, final in (("origin", 0.0), ("spacing", 1.0)):
                    if p.get(key) is not None and len(p[key]) == 3:
                        p[key] = list(p[key]) + [final]
            image_item.set_image_properties(**p)


_process_data_item_container_class(AMDMImageContainer)


class ActorOutputAMDM(ActorOutputImage):
    """Raw-first merge semantics with the legacy AMDM MetaImage filenames."""

    data_container_class = AMDMImageContainer
    _suffixes = {
        0: "restrictedEdep",
        1: "unprocessedForMergingOnly-delta",
        2: "unprocessedForMergingOnly-gamma",
        "delta": "delta",
        "gamma": "gamma",
    }

    def _insert_item_suffix(self, output_filename, item):
        """Resolve an item's legacy MetaImage name from an actor-wide basename.

        Remove only the final extension, retain the parent directory, and
        preserve the framework's None, empty and automatic filename markers.
        """
        if output_filename in (None, "", "auto"):
            return output_filename
        path = Path(output_filename)
        # The legacy contract removes the final extension, including .gz only
        # for a basename ending in .nii.gz. AMDM image outputs are always .mhd.
        return str(path.with_name(f"{path.stem}-{self._suffixes[item]}.mhd"))


process_cls(ActorOutputAMDM)
