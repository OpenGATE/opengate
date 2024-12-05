from .opengate_core import *
from .g4DataSetup import *
from .qt5Setup import *


if os.environ.get("GATEONRTD", None) is None:
    check_g4_data()
    set_g4_data_path()
    set_qt5_path()
