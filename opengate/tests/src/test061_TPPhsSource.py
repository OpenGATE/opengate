import test061_TPPhsSource_helpers as t
import opengate as gate
from scipy.spatial.transform import Rotation
from opengate.tests import utility

from opengate.contrib.tps.treatmentPlanPhsSource import TreatmentPlanPhsSource
from opengate.contrib.tps.ionbeamtherapy import spots_info_from_txt, TreatmentPlanSource


paths = utility.get_default_test_paths(__file__, "test061_TPPhsSource")
paths.output_ref = paths.output_ref / "test061_ref"

ref_path = paths.output_ref

# units
m = gate.g4_units.m
mm = gate.g4_units.mm
cm = gate.g4_units.cm
nm = gate.g4_units.nm
Bq = gate.g4_units.Bq
MeV = gate.g4_units.MeV
deg: float = gate.g4_units.deg


def main():
    # print("create reference PhS file")
    # t.create_test_Phs(
    #     particle="proton",
    #     phs_name=paths.output / "test_proton",
    #     number_of_particles=1,
    #     translation=[0 * cm, 0 * cm, 0 * mm],
    # )
    print("Testing TPPhS source rotations")

    t.test_source_rotation_A(
        plan_file_name=ref_path / "PlanSpot.txt",
        phs_list_file_name="PhsList.txt",
        phs_folder_name=ref_path,
        phs_file_name_out=paths.output / "output.root",
    )

    a = t.check_value_from_root_file(
        file_name_root=paths.output / "output.root",
        key="KineticEnergy",
        ref_value=150 * MeV,
    )
    b = t.check_value_from_root_file(
        file_name_root=paths.output / "output.root",
        key="PrePositionLocal_X",
        ref_value=-60,
    )
    c = t.check_value_from_root_file(
        file_name_root=paths.output / "output.root",
        key="PrePositionLocal_Y",
        ref_value=50,
    )
    d = t.check_value_from_root_file(
        file_name_root=paths.output / "output.root",
        key="PrePositionLocal_Z",
        ref_value=0,
    )

    e = t.check_value_from_root_file(
        file_name_root=paths.output / "output.root",
        key="PreDirectionLocal_X",
        ref_value=-0.012,
    )
    f = t.check_value_from_root_file(
        file_name_root=paths.output / "output.root",
        key="PreDirectionLocal_Y",
        ref_value=0.01,
    )

    # this is the end, my friend
    utility.test_ok(a and b and c and d and e and f)


if __name__ == "__main__":
    main()
