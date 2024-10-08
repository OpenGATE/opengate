import sys
import inspect

from . import image, listmode, sequences, datafetchers, utility

# import inspect
#
# available_processing_units = {}
# g = globals().copy()
# for name, obj in g.items():
#     if inspect.isclass(obj):
#         available_processing_units[name] = obj
# print(available_processing_units)

available_processing_units = {
    "ProjectionListMode": image.ProjectionListMode,
    "ProcessingSequence": sequences.ProcessingSequence,
    "GaussianBlurringSingleAttribute": listmode.GaussianBlurringSingleAttribute,
    "OffsetSingleAttribute": listmode.OffsetSingleAttribute,
    "DataFetcherHdf5": datafetchers.DataFetcherHdf5,
}

clsmembers = inspect.getmembers(sys.modules[__name__], inspect.isclass)
