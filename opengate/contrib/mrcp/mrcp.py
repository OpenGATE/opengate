from __future__ import annotations

import math
from dataclasses import dataclass
from pathlib import Path
from types import SimpleNamespace
from typing import Dict, Iterable, List, Tuple

from opengate.actors.filters import CopyNumberFilter

from . import mrcp_utils as h


@dataclass
class MRCPPhantomInfo:
    """Bookkeeping object returned by add_mrcp_phantom."""

    volume: object
    id_to_name: Dict[int, str]
    geometry_region_ids: List[int]
    scoring_region_ids: List[int]
    region_to_copy_numbers: Dict[int, List[int]]
    selected_copy_numbers: List[int]
    node_bounds: Tuple[Tuple[float, float, float], Tuple[float, float, float]]
    ele_file_used: Path
    work_dir: Path
    container_margin_mm: float
    use_filtered_geometry: bool = False


@dataclass
class MRCPDoseSettings:
    """Settings used by add_mrcp_dose_actors."""

    spacing_mm: float = 2.5
    output_subdir: str = "dose_by_region"
    max_regions: int = 400
    aggregate_selected_regions: bool = True
    per_region: bool = True
    full_grid: bool = False
    write_to_disk: bool = True
    hit_type: str = "random"
    output_coordinate_system: str = "local"
    enable_dose_output: bool = False
    enable_dose_uncertainty: bool = False
    enable_edep_uncertainty: bool = False
    debug: bool = False


def _as_path(path_like) -> Path:
    return Path(path_like).expanduser().resolve()


def _copy_filter(name: str, copy_numbers: Iterable[int]) -> CopyNumberFilter:
    filt = CopyNumberFilter(name=name)
    filt.copy_numbers = [int(x) for x in copy_numbers]
    return filt


def add_mrcp_phantom(
    simulation,
    name: str = "mrcp",
    data_path: str | Path = ".",
    phantom_type: str = "adult_female",
    node_file: str = "MRCP_AF.node",
    ele_file: str = "MRCP_AF.ele",
    material_file: str = "MRCP_AF.material",
    color_file: str = "colour.dat",
    scoring_keywords: Iterable[str] = ("heart", "lung"),
    geometry_keywords: Iterable[str] = (),
    show_all_organs: bool = True,
    vis_hide_keywords: Iterable[str] = (),
    vis_only_keywords: Iterable[str] = (),
    work_dir: str | Path = "output_g4tet_mrcp",
    phantom_z_mm: float = 0.0,
    container_margin_mm: float = 0.0,
    check_overlaps: bool = False,
):
    """Add an MRCP Tet mesh phantom to an OpenGATE simulation.

    This is a first contrib-style wrapper around the validated MRCP prototype.
    Adult-female (MRCP_AF) and adult-male (MRCP_AM) TetGen phantoms are
    supported. Selecting an adult-male phantom automatically changes the
    default AF input filenames to their AM equivalents; explicitly supplied
    filenames are left unchanged.
    """

    allowed_phantom_types = {
        "adult_female",
        "MRCP_AF",
        "mrcp_af",
        "adult_male",
        "MRCP_AM",
        "mrcp_am",
    }
    if phantom_type not in allowed_phantom_types:
        raise ValueError(
            f"Unsupported phantom_type={phantom_type!r}. "
            "Currently supported: adult_female / MRCP_AF / "
            "adult_male / MRCP_AM."
        )

    if phantom_type in {"adult_male", "MRCP_AM", "mrcp_am"}:
        if node_file == "MRCP_AF.node":
            node_file = "MRCP_AM.node"
        if ele_file == "MRCP_AF.ele":
            ele_file = "MRCP_AM.ele"
        if material_file == "MRCP_AF.material":
            material_file = "MRCP_AM.material"

    units = h.define_units()
    mm = units["mm"]
    cm = units["cm"]

    data_dir = _as_path(data_path)
    work_path = Path(work_dir)
    work_path.mkdir(parents=True, exist_ok=True)

    node_path = _as_path(data_dir / node_file)
    ele_path = _as_path(data_dir / ele_file)
    material_path = _as_path(data_dir / material_file)
    color_path = _as_path(data_dir / color_file)

    id_to_name, geometry_keep_ids, score_keep_ids = h.select_region_ids(
        material_path,
        list(geometry_keywords),
        list(scoring_keywords),
        bool(show_all_organs),
    )
    if not geometry_keep_ids:
        raise RuntimeError("No regions matched the MRCP geometry selection.")
    if not score_keep_ids:
        raise RuntimeError("No regions matched the MRCP scoring selection.")

    use_filtered_geometry = (
        not show_all_organs
        and bool(geometry_keep_ids)
        and set(int(x) for x in geometry_keep_ids) != set(int(x) for x in id_to_name.keys())
    )
    if use_filtered_geometry:
        ele_use = work_path / f"{name}_filtered.ele"
        kept = h.filter_ele_stream(ele_path, ele_use, geometry_keep_ids)
        if kept <= 0:
            raise RuntimeError("Filtered MRCP .ele file kept 0 tetrahedra.")
    else:
        ele_use = ele_path

    region_to_copy_numbers = h.build_region_copy_map(ele_use)
    selected_copy_numbers = h.flatten_selected_copy_numbers(
        region_to_copy_numbers, score_keep_ids
    )
    bbox_native = h.read_node_bounds(node_path)
    (gminx, gminy, gminz), (gmaxx, gmaxy, gmaxz) = bbox_native
    center_x = 0.5 * (gminx + gmaxx)
    center_y = 0.5 * (gminy + gmaxy)
    center_z = 0.5 * (gminz + gmaxz)
    world_center_tr = [
        center_x * cm,
        center_y * cm,
        center_z * cm + float(phantom_z_mm) * mm,
    ]

    color_file_to_use = h.resolve_visual_color_file(
        color_path,
        material_path,
        work_path,
        id_to_name,
        list(vis_only_keywords),
        list(vis_hide_keywords),
    )

    phantom = simulation.add_volume("TetrahedralMesh", name)
    phantom.mother = "world"
    phantom.translation = list(world_center_tr)
    phantom.material = "G4_Galactic"
    phantom.node_file = str(node_path)
    phantom.ele_file = str(ele_use)
    phantom.material_file = str(material_path)
    phantom.color_file = str(color_file_to_use)
    phantom.container_margin_mm = float(container_margin_mm)
    if use_filtered_geometry:
        phantom.keep_regions = [int(x) for x in geometry_keep_ids]
    phantom.pv_name = f"{name}_env"
    phantom.check_overlaps = bool(check_overlaps)
    h.set_first_supported(phantom, ["default_material", "defaultMaterial"], "G4_Galactic")

    total_tets = sum(len(v) for v in region_to_copy_numbers.values())
    print(
        f"[OK] MRCP phantom '{name}' ready: total tetrahedra={total_tets}, "
        f"selected scoring tetrahedra={len(selected_copy_numbers)}"
    )

    return MRCPPhantomInfo(
        volume=phantom,
        id_to_name=id_to_name,
        geometry_region_ids=[int(x) for x in geometry_keep_ids],
        scoring_region_ids=[int(x) for x in score_keep_ids],
        region_to_copy_numbers=region_to_copy_numbers,
        selected_copy_numbers=selected_copy_numbers,
        node_bounds=bbox_native,
        ele_file_used=Path(ele_use),
        work_dir=work_path,
        container_margin_mm=float(container_margin_mm),
        use_filtered_geometry=use_filtered_geometry,
    )


def add_mrcp_dose_actors(
    simulation,
    phantom: MRCPPhantomInfo,
    units,
    settings: MRCPDoseSettings | None = None,
):
    """Add aggregate and per-region MRCP edep actors."""

    settings = settings or MRCPDoseSettings()
    uniq_ids = sorted(set(int(x) for x in phantom.scoring_region_ids))
    if len(uniq_ids) > int(settings.max_regions):
        raise RuntimeError(
            f"Too many MRCP regions selected ({len(uniq_ids)}). "
            "Refine scoring keywords or increase max_regions."
        )

    output_subdir = str(settings.output_subdir)
    (Path(simulation.output_dir) / output_subdir).mkdir(parents=True, exist_ok=True)

    spacing = float(settings.spacing_mm) * units["mm"]
    (full_sx, full_sy, full_sz), _ = phantom.volume.get_bbox_size_and_center_mm()
    grid_size = [
        max(1, int(math.ceil(full_sx / settings.spacing_mm))),
        max(1, int(math.ceil(full_sy / settings.spacing_mm))),
        max(1, int(math.ceil(full_sz / settings.spacing_mm))),
    ]
    grid_translation = [0 * units["mm"], 0 * units["mm"], 0 * units["mm"]]

    if settings.debug:
        print(
            f"[DBG] MRCP dose grid size={grid_size}, "
            f"spacing_mm={settings.spacing_mm}"
        )

    actor_cfg = {
        "write_to_disk": settings.write_to_disk,
        "hit_type": settings.hit_type,
        "output_coordinate_system": settings.output_coordinate_system,
        "enable_dose_output": settings.enable_dose_output,
        "enable_dose_uncertainty": settings.enable_dose_uncertainty,
        "enable_edep_uncertainty": settings.enable_edep_uncertainty,
    }
    created = []
    scoring_requires_filter = bool(phantom.selected_copy_numbers)

    if settings.full_grid:
        actor = h.make_common_dose_actor(
            simulation,
            "Dose_unfiltered_fullgrid",
            phantom.volume,
            grid_size,
            [spacing, spacing, spacing],
            grid_translation,
            f"{output_subdir}/unfiltered_fullgrid",
            actor_cfg,
        )
        created.append(("unfiltered_fullgrid", actor))

    if settings.aggregate_selected_regions:
        actor = h.make_common_dose_actor(
            simulation,
            "Dose_selected_regions",
            phantom.volume,
            grid_size,
            [spacing, spacing, spacing],
            grid_translation,
            f"{output_subdir}/selected_regions",
            actor_cfg,
        )
        if scoring_requires_filter:
            actor.filter = _copy_filter(
                "CF_selected_regions", phantom.selected_copy_numbers
            )
        created.append(("selected_regions", actor))

    if settings.per_region:
        for rid in uniq_ids:
            matname = phantom.id_to_name.get(rid, f"region_{rid}")
            vol_name = f"{h.sanitize_volume_name(matname)}_{rid}"
            actor = h.make_common_dose_actor(
                simulation,
                f"Dose_{vol_name}",
                phantom.volume,
                grid_size,
                [spacing, spacing, spacing],
                grid_translation,
                f"{output_subdir}/{vol_name}",
                actor_cfg,
            )
            actor.filter = _copy_filter(
                f"CF_{vol_name}",
                phantom.region_to_copy_numbers.get(int(rid), []),
            )
            created.append((vol_name, actor))

    print(
        f"[OK] Created {len(created)} MRCP dose actor(s). "
        f"Outputs: {Path(simulation.output_dir) / output_subdir}"
    )
    return created


def load_mrcp_json_config(config_path: str | Path) -> SimpleNamespace:
    return h.apply_config(h.load_json_config(Path(config_path)))
