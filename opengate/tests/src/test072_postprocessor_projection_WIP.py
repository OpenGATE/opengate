import tables
import numpy as np

from opengate.postprocessors.base import PostProcessor
from opengate import Simulation

__run_group_prefix__ = "data_from_run"


def create_mock_data(path):
    n_rows = int(1e5)

    class Attributes(tables.IsDescription):
        event_id = tables.FloatCol(pos=1)
        particle = tables.StringCol(itemsize=16, pos=2)
        energy = tables.FloatCol(pos=3)
        position = tables.FloatCol(shape=(3,), pos=4)

    # dt = np.dtype([('event_id', np.float32),
    #                ('particle', 'S20'),
    #                ('energy', np.float32),
    #                ('position', np.float32),
    #                ])

    with tables.open_file(path, mode="w", title="Test file") as h5file:
        runs = list(range(10))
        for g_name in [f"{__run_group_prefix__}_{r}" for r in runs] + ["merged_data"]:
            group = h5file.create_group("/", g_name, f"Data from {g_name}")
            table = h5file.create_table(group, "singles", description=Attributes)
            table.cols.energy.attrs["unit"] = "MeV"

            arr_event_id = np.arange(n_rows)
            arr_energy = np.ones(n_rows).reshape(n_rows) * 300
            arr_particles = np.array(["proton"] * n_rows)

            x = np.random.randn(n_rows) * 20
            y = np.random.randn(n_rows) * 20
            z = np.ones_like(x)
            arr_position = np.vstack((x, y, z)).T

            table.append([arr_event_id, arr_particles, arr_energy, arr_position])


path = "postprocessor_test.h5"
create_mock_data(path)

sim = Simulation()
sim.output_path = "."

post_processor = PostProcessor(name="post_processor", simulation=sim)

datafetcher = post_processor.add_processing_unit(
    "DataFetcherHdf5",
    name="datafetcher",
    input_path="postprocessor_test.h5",
    hdf5_node_name="singles",
    input_hdf5_group="/merged_data",
)

# sequence = post_processor.add_processing_unit('ProcessingSequence', name='sequence1')
#
# gaussian_blurrer_energy = sequence.add_processing_unit('GaussianBlurringSingleAttribute',
#                                                        name='blurrer_energy',
#                                                        attribute='energy',
#                                                        sigma=10)
#
# gaussian_blurrer_position = sequence.add_processing_unit('GaussianBlurringSingleAttribute',
#                                                          name='blurrer_position',
#                                                          attribute='position',
#                                                          sigma=10)
#
# offsetter_energy = sequence.add_processing_unit('OffsetSingleAttribute',
#                                                 name='offset_energy',
#                                                 attribute='energy',
#                                                 offset=10)

projector = post_processor.add_processing_unit(
    "ProjectionListMode", name="projector", size=[100, 100, 1], spacing=[1.2, 0.9, 1]
)


#
# # gaussian_blurrer_energy = GaussianBlurringSingleAttribute(name='blurrer_energy',
# #                                                           attribute='energy',
# #                                                           sigma=10)
# #
# # gaussian_blurrer_position = GaussianBlurringSingleAttribute(name='blurrer_position',
# #                                                             attribute='position',
# #                                                             sigma=10)
# #
# # offsetter_energy = OffsetSingleAttribute(name='offset_energy',
# #                                          attribute='energy',
# #                                          offset=10)
# # datafetcher = DataFetcherHdf5(name='datafetcher',
# #                               input_path="postprocessor_test.h5",
# #                               hdf5_node_name='singles',
# #                               path_in_hdf5_file='/merged_data')
# #
# #
# # sequence1 = ProcessingSequence(name='sequence1')
#
# sequence1.add_processing_unit(gaussian_blurrer_energy)
# sequence1.add_processing_unit(gaussian_blurrer_position)
# sequence1.add_processing_unit(offsetter_energy)


# post_processor.add_processing_unit(datafetcher)
# post_processor.add_processing_unit(sequence1)

# post_processor.initialize()

post_processor.run()
