import numpy as np

from .unitbase import ProcessingUnitBase
from ..exception import fatal
from .utility import get_table_column


class ListModeSingleAttribute(ProcessingUnitBase):
    _required_number_of_input_units = 1

    user_info_defaults = {
        "attribute": (
            0,
            {
                "doc": "Name of the attribute to be blurred.",
            },
        ),
    }

    def assert_input_is_compatible(self):
        if len(self.children) != self._required_number_of_input_units:
            fatal(f"Too many input units. This unit accepts only one. ")

    def initialize_output_data_handle(self):
        input_data_handle = self.input_units[0].output_data_handle
        self.output_data_handle = input_data_handle.copy(
            newparent=self.hdf5_group
        )  # , newname=get_node_name(input_data_handle))

    def get_table_column_to_work_on(self):
        if self.output_data_handle is None:
            self.initialize_output_data_handle()
        return get_table_column(self.output_data_handle, self.attribute)


class GaussianBlurringSingleAttribute(ListModeSingleAttribute):
    user_info_defaults = {
        "sigma": (
            0,
            {
                "doc": "1-sigma width of the blurring kernel.",
            },
        ),
    }

    def do_your_job(self):
        column = self.get_table_column_to_work_on()
        try:
            attribute_size = column.shape[1]
        except IndexError:
            attribute_size = 1
        try:
            sigma_size = len(self.sigma)
        except TypeError:
            sigma_size = 1
        if sigma_size == 1:
            sigma = np.array([self.sigma] * attribute_size)
            # perturbation = np.random.randn(len(column)) * self.sigma
        elif sigma_size == attribute_size:
            sigma = np.array([self.sigma])
        else:
            fatal(
                f"User inout sigma={self.sigma} incompatible with the attribute of length {attribute_size}."
            )

        perturbation = np.multiply(
            np.random.randn(len(column) * len(sigma)).reshape(len(column), len(sigma)),
            sigma,
        ).squeeze()
        column[:] += perturbation


class OffsetSingleAttribute(ListModeSingleAttribute):
    user_info_defaults = {
        "offset": (
            0,
            {
                "doc": "1-sigma width of the blurring kernel.",
            },
        ),
    }

    def do_your_job(self):
        column = self.get_table_column_to_work_on()  # this is a column object
        column[:] += self.offset  # with [:], we get an array
