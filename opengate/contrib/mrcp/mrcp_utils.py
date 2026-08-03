from __future__ import annotations

import colorsys
import json
import math
import re
from pathlib import Path
from types import SimpleNamespace
from typing import Dict, List, Tuple

import opengate as gate
import opengate_core as g4

from opengate.exception import fatal


_Z2_SYMBOL = {
    1: "H", 2: "He", 3: "Li", 4: "Be", 5: "B", 6: "C", 7: "N",
    8: "O", 9: "F", 10: "Ne", 11: "Na", 12: "Mg", 13: "Al", 14: "Si",
    15: "P", 16: "S", 17: "Cl", 18: "Ar", 19: "K", 20: "Ca", 21: "Sc",
    22: "Ti", 23: "V", 24: "Cr", 25: "Mn", 26: "Fe", 27: "Co",
    28: "Ni", 29: "Cu", 30: "Zn", 31: "Ga", 32: "Ge", 33: "As",
    34: "Se", 35: "Br", 36: "Kr", 37: "Rb", 38: "Sr", 39: "Y",
    40: "Zr", 41: "Nb", 42: "Mo", 43: "Tc", 44: "Ru", 45: "Rh",
    46: "Pd", 47: "Ag", 48: "Cd", 49: "In", 50: "Sn", 51: "Sb",
    52: "Te", 53: "I", 54: "Xe", 55: "Cs", 56: "Ba", 57: "La",
    58: "Ce", 59: "Pr", 60: "Nd", 61: "Pm", 62: "Sm", 63: "Eu",
    64: "Gd", 65: "Tb", 66: "Dy", 67: "Ho", 68: "Er", 69: "Tm",
    70: "Yb", 71: "Lu", 72: "Hf", 73: "Ta", 74: "W", 75: "Re",
    76: "Os", 77: "Ir", 78: "Pt", 79: "Au", 80: "Hg", 81: "Tl",
    82: "Pb", 83: "Bi", 84: "Po", 85: "At", 86: "Rn", 87: "Fr",
    88: "Ra", 89: "Ac", 90: "Th", 91: "Pa", 92: "U", 93: "Np",
    94: "Pu", 95: "Am", 96: "Cm", 97: "Bk", 98: "Cf", 99: "Es",
    100: "Fm", 101: "Md", 102: "No", 103: "Lr", 104: "Rf", 105: "Db",
    106: "Sg", 107: "Bh", 108: "Hs", 109: "Mt", 110: "Ds", 111: "Rg",
    112: "Cn", 113: "Nh", 114: "Fl", 115: "Mc", 116: "Lv", 117: "Ts",
    118: "Og",
}

_G4_MATERIAL_CACHE = {}


def parse_mrcp_material_file(material_file: str):
    """Parse MRCP material blocks into compositions and region names."""

    material_definitions = {}
    region_to_name = {}
    current_name = None
    current_density = None
    current_fractions = {}

    def flush_material():
        nonlocal current_name, current_density, current_fractions
        if current_name is None:
            return
        total = sum(current_fractions.values())
        if total <= 0:
            fatal(
                f"Empty composition for material '{current_name}' "
                f"in {material_file}"
            )
        normalized = {
            atomic_number: fraction / total
            for atomic_number, fraction in current_fractions.items()
        }
        material_definitions[current_name] = {
            "density_g_cm3": float(current_density),
            "zfrac": normalized,
        }
        current_name = None
        current_density = None
        current_fractions = {}

    with open(material_file, "r") as material_stream:
        for line in material_stream:
            stripped = line.strip()
            if not stripped:
                continue

            if stripped.startswith("C"):
                tokens = stripped.split()
                if len(tokens) >= 3 and tokens[0] == "C":
                    flush_material()
                    current_name = tokens[1]
                    current_density = float(tokens[2])
                else:
                    flush_material()
                continue

            tokens = stripped.split()
            if tokens[0].startswith("m") and tokens[0][1:].isdigit():
                if current_name is None:
                    fatal(
                        f"Found region line before material header in "
                        f"{material_file}: {stripped}"
                    )
                region_id = int(tokens[0][1:])
                region_to_name[region_id] = current_name
                if len(tokens) < 3:
                    continue
                element_code = int(tokens[1])
                fraction = abs(float(tokens[2]))
            else:
                if len(tokens) < 2:
                    continue
                element_code = int(tokens[0])
                fraction = abs(float(tokens[1]))

            atomic_number = element_code // 1000
            if atomic_number > 0:
                current_fractions[atomic_number] = (
                    current_fractions.get(atomic_number, 0.0) + fraction
                )

    flush_material()
    return material_definitions, region_to_name


def ensure_custom_material_from_zfrac(
    name: str, density_g_cm3: float, zfrac: dict
):
    """Build or reuse a Geant4 material from element mass fractions."""

    if name in _G4_MATERIAL_CACHE:
        return _G4_MATERIAL_CACHE[name]
    if density_g_cm3 <= 0 or density_g_cm3 > 30:
        fatal(f"Unreasonable density for '{name}': {density_g_cm3} g/cm3")

    material = g4.G4Material(
        name,
        float(density_g_cm3) * gate.g4_units.g_cm3,
        len(zfrac),
        g4.kStateSolid,
        293.15,
        1.0,
    )
    nist = g4.G4NistManager.Instance()
    for atomic_number, fraction in zfrac.items():
        symbol = _Z2_SYMBOL.get(int(atomic_number))
        if symbol is None:
            fatal(f"Unknown atomic number Z={atomic_number} for material '{name}'")
        material.AddElement(nist.FindOrBuildElement(symbol), float(fraction))

    _G4_MATERIAL_CACHE[name] = material
    return material


def parse_colour_dat(color_file: str):
    """Parse MRCP colour entries into RGBA and visibility mappings."""

    output = {}
    if color_file is None or str(color_file).strip() == "":
        return output
    color_path = Path(color_file)
    if not color_path.exists():
        return output

    with color_path.open("r", encoding="utf-8", errors="ignore") as stream:
        for line in stream:
            stripped = line.strip()
            if not stripped or stripped.startswith("#"):
                continue
            tokens = stripped.replace(",", " ").split()
            key = int(tokens[0]) if tokens[0].lstrip("+-").isdigit() else tokens[0]
            numbers = []
            for token in tokens[1:]:
                try:
                    numbers.append(float(token))
                except ValueError:
                    continue
            if len(numbers) < 3:
                continue

            red, green, blue = numbers[:3]
            alpha_or_visibility = numbers[3] if len(numbers) >= 4 else 1.0
            if alpha_or_visibility in (0.0, 1.0):
                visible = bool(int(alpha_or_visibility))
                rgba = [red, green, blue, 1.0]
            else:
                visible = alpha_or_visibility > 0.0
                rgba = [red, green, blue, alpha_or_visibility]
            output[key] = (rgba, visible)
    return output


def define_units():
    units = gate.g4_units
    return {
        "m": units.m,
        "mm": units.mm,
        "cm": units.cm,
        "keV": units.keV,
        "Bq": units.Bq,
        "deg": units.deg,
        "g_cm3": units.g_cm3,
    }


def sanitize_volume_name(name: str) -> str:
    out = re.sub(r"[^A-Za-z0-9_]+", "_", str(name)).strip("_")
    if not out:
        out = "region"
    if out[0].isdigit():
        out = "r_" + out
    return out[:120]


def try_set(obj, attr: str, value) -> None:
    try:
        setattr(obj, attr, value)
    except Exception:
        pass


def set_first_supported(obj, candidates: List[str], value):
    for attr in candidates:
        try:
            setattr(obj, attr, value)
            return attr
        except Exception:
            continue
    return None


def load_json_config(config_path: Path) -> dict:
    if not config_path.exists():
        raise FileNotFoundError(f"Configuration file not found: {config_path}")
    filtered_lines = []
    for line in config_path.read_text(encoding="utf-8").splitlines():
        stripped = line.lstrip()
        if stripped.startswith("//") or stripped.startswith("#"):
            continue
        filtered_lines.append(line)
    data = json.loads("\n".join(filtered_lines))
    if not isinstance(data, dict):
        raise TypeError(f"Configuration root must be a JSON object: {config_path}")
    return data


def apply_config(config: dict) -> SimpleNamespace:
    return SimpleNamespace(
        node_file=str(config.get("node_file", "MRCP_AF.node")),
        ele_file=str(config.get("ele_file", "MRCP_AF.ele")),
        material_file=str(config.get("material_file", "MRCP_AF.material")),
        color_file=str(config.get("color_file", "colour.dat")),
        container_margin_mm=float(config.get("container_margin_mm", 0.0)),
        phantom_z_mm=float(config.get("phantom_z_mm", 0.0)),
        check_overlaps=bool(config.get("check_overlaps", False)),
        random_seed=config.get("random_seed", "auto"),
        output_dir=str(config.get("output_dir", "output_mrcp")),
        work_dir=str(config.get("work_dir", "output_g4tet_mrcp")),
        dose_output_subdir=str(config.get("dose_output_subdir", "dose_by_region")),
        region_dose=bool(config.get("region_dose", True)),
        max_regions=int(config.get("max_regions", 400)),
        debug_dose=bool(config.get("debug_dose", False)),
        activity_bq=float(config.get("activity_bq", 10.0)),
        kvp=float(config.get("kvp", 120.0)),
        theta_e_target=float(config.get("theta_e_target", 7.0)),
        physics_list=str(config.get("physics_list", "G4EmStandardPhysics_option4")),
        keywords=list(config.get("scoring_keywords", [])),
        geometry_keywords=list(config.get("geometry_keywords", [])),
        show_all_organs=bool(config.get("show_all_organs", False)),
        aggregate_selected_regions=bool(config.get("aggregate_selected_regions", True)),
        per_region_dose=bool(config.get("per_region_dose", False)),
        full_grid_dose=bool(config.get("full_grid_dose", False)),
        vis_hide_keywords=list(config.get("vis_hide_keywords", [])),
        vis_only_keywords=list(config.get("vis_only_keywords", [])),
        timing=bool(config.get("timing", False)),
        number_of_threads=int(config.get("number_of_threads", 1)),
        run_events=int(config.get("run_events", 100)),
        build_vis_events=int(config.get("build_vis_events", 0)),
        dose_spacing_mm=float(config.get("dose_spacing_mm", 2.5)),
        write_to_disk=bool(config.get("write_to_disk", True)),
        output_coordinate_system=str(config.get("output_coordinate_system", "local")),
        hit_type=str(config.get("hit_type", "random")),
        enable_dose_output=bool(config.get("enable_dose_output", False)),
        enable_dose_uncertainty=bool(config.get("enable_dose_uncertainty", False)),
        enable_edep_uncertainty=bool(config.get("enable_edep_uncertainty", False)),
    )


def read_node_bounds(node_path: Path) -> Tuple[Tuple[float, float, float], Tuple[float, float, float]]:
    minx = miny = minz = float("inf")
    maxx = maxy = maxz = float("-inf")

    with node_path.open("r", encoding="utf-8", errors="ignore") as stream:
        for line in stream:
            stripped = line.strip()
            if stripped and not stripped.startswith("#"):
                break
        for line in stream:
            stripped = line.strip()
            if not stripped or stripped.startswith("#"):
                continue
            toks = stripped.split()
            if len(toks) < 4:
                continue
            try:
                x, y, z = float(toks[1]), float(toks[2]), float(toks[3])
            except Exception:
                continue
            minx, miny, minz = min(minx, x), min(miny, y), min(minz, z)
            maxx, maxy, maxz = max(maxx, x), max(maxy, y), max(maxz, z)

    if not math.isfinite(minx):
        raise ValueError(f"Could not parse any nodes from: {node_path}")
    return (minx, miny, minz), (maxx, maxy, maxz)


def filter_ele_stream(ele_path: Path, out_ele_path: Path, keep_ids: List[int]) -> int:
    keep = {int(x) for x in keep_ids}
    out_ele_path.parent.mkdir(parents=True, exist_ok=True)

    body_tmp = out_ele_path.with_suffix(out_ele_path.suffix + ".body.tmp")
    kept = 0
    nodes_per_tet = 4
    nattr = 0

    with ele_path.open("r", encoding="utf-8", errors="ignore") as fin, body_tmp.open(
        "w", encoding="utf-8"
    ) as body:
        for line in fin:
            stripped = line.strip()
            if not stripped or stripped.startswith("#"):
                continue
            header = stripped.split()
            if len(header) >= 3:
                try:
                    nodes_per_tet = int(float(header[1]))
                    nattr = int(float(header[2]))
                except Exception:
                    nodes_per_tet, nattr = 4, 0
            break

        for line in fin:
            stripped = line.strip()
            if not stripped or stripped.startswith("#"):
                continue
            toks = stripped.split()
            if len(toks) < 1 + nodes_per_tet + 1:
                continue
            try:
                rid = int(float(toks[-1]))
            except Exception:
                continue
            if rid in keep:
                body.write(stripped + "\n")
                kept += 1

    with out_ele_path.open("w", encoding="utf-8") as fout, body_tmp.open(
        "r", encoding="utf-8"
    ) as body:
        fout.write(f"{kept} {nodes_per_tet} {nattr}\n")
        for line in body:
            fout.write(line)

    try:
        body_tmp.unlink()
    except Exception:
        pass

    return kept


def build_region_copy_map(ele_path: Path) -> Dict[int, List[int]]:
    region_to_copies: Dict[int, List[int]] = {}
    nodes_per_tet = 4

    with ele_path.open("r", encoding="utf-8", errors="ignore") as stream:
        for line in stream:
            stripped = line.strip()
            if not stripped or stripped.startswith("#"):
                continue
            header = stripped.split()
            if len(header) >= 3:
                try:
                    nodes_per_tet = int(float(header[1]))
                except Exception:
                    nodes_per_tet = 4
            break

        copy_no = 0
        for line in stream:
            stripped = line.strip()
            if not stripped or stripped.startswith("#"):
                continue
            toks = stripped.split()
            if len(toks) < 1 + nodes_per_tet + 1:
                continue
            try:
                rid = int(float(toks[-1]))
            except Exception:
                continue
            region_to_copies.setdefault(rid, []).append(copy_no)
            copy_no += 1

    return region_to_copies


def flatten_selected_copy_numbers(
    region_to_copy_numbers: Dict[int, List[int]], selected_region_ids: List[int]
) -> List[int]:
    out: List[int] = []
    for rid in selected_region_ids:
        out.extend(region_to_copy_numbers.get(int(rid), []))
    return out


def load_material_table_and_select(material_path: Path, keywords: List[str]):
    kws = [k.lower() for k in (keywords or []) if str(k).strip()]

    def match(name: str) -> bool:
        if not kws:
            return True
        lowered = name.lower()
        return any(k in lowered for k in kws)

    lines = [
        line.strip()
        for line in material_path.read_text(encoding="utf-8", errors="ignore").splitlines()
        if line.strip()
    ]
    i = 0
    id_to_name: Dict[int, str] = {}
    keep_ids: List[int] = []
    keep_names: List[str] = []

    while i < len(lines):
        if not lines[i].startswith("C"):
            i += 1
            continue

        parts = lines[i].split()
        if len(parts) < 2:
            i += 1
            continue

        name = parts[1]
        i += 1
        region_id = None

        while i < len(lines) and not lines[i].startswith("C"):
            toks = lines[i].split()
            if toks and toks[0].startswith("m"):
                try:
                    region_id = int(toks[0][1:])
                except Exception:
                    region_id = None
            i += 1

        if region_id is None:
            continue

        id_to_name[region_id] = name
        if not match(name):
            continue
        keep_ids.append(region_id)
        keep_names.append(name)

    seen = set()
    out_ids: List[int] = []
    out_names: List[str] = []
    for rid, name in zip(keep_ids, keep_names):
        if rid in seen:
            continue
        seen.add(rid)
        out_ids.append(rid)
        out_names.append(name)

    return id_to_name, out_ids, out_names


def select_region_ids(
    material_path: Path,
    geometry_keywords: List[str],
    scoring_keywords: List[str],
    show_all_organs: bool,
):
    id_to_name, all_ids, _ = load_material_table_and_select(material_path, [])
    _, score_ids, _ = load_material_table_and_select(material_path, list(scoring_keywords))

    if show_all_organs:
        geometry_ids = list(all_ids)
    elif geometry_keywords:
        _, geometry_ids, _ = load_material_table_and_select(material_path, list(geometry_keywords))
    else:
        geometry_ids = list(score_ids)

    return id_to_name, geometry_ids, score_ids


def create_hidden_only_colour_file(color_in: Path, outdir: Path, hidden_ids: List[int]) -> Path:
    if not color_in.exists():
        return color_in

    hidden_set = {int(x) for x in hidden_ids}
    out_path = outdir / f"{color_in.stem}_hide_h{len(hidden_set)}{color_in.suffix}"

    with color_in.open("r", encoding="utf-8", errors="ignore") as fin, out_path.open(
        "w", encoding="utf-8"
    ) as fout:
        for line in fin:
            stripped = line.strip()
            if not stripped or stripped.startswith("#"):
                fout.write(line)
                continue
            toks = stripped.split()
            key = toks[0]
            try:
                key_int = int(float(key))
            except Exception:
                key_int = None

            vals = toks[1:]
            if len(vals) >= 3 and key_int is not None:
                r, g, b = vals[0], vals[1], vals[2]
                if key_int in hidden_set:
                    fout.write(f"{key} {r} {g} {b} 0.000\n")
                else:
                    a = vals[3] if len(vals) >= 4 else "1.000"
                    fout.write(f"{key} {r} {g} {b} {a}\n")
            else:
                fout.write(line)
    return out_path


def create_distinct_colour_file(
    color_in: Path,
    outdir: Path,
    id_to_name: Dict[int, str],
    hidden_ids: List[int],
) -> Path:
    if not color_in.exists():
        return color_in

    hidden_set = {int(x) for x in hidden_ids}
    out_path = outdir / f"{color_in.stem}_distinct_h{len(hidden_set)}{color_in.suffix}"
    visible_ids = sorted(int(rid) for rid in id_to_name.keys() if int(rid) not in hidden_set)
    count = max(1, len(visible_ids))
    palette = {}
    for idx, rid in enumerate(visible_ids):
        hue = (idx / count) % 1.0
        r, g, b = colorsys.hsv_to_rgb(hue, 0.75, 0.95)
        palette[rid] = (r, g, b, 1.0)

    with color_in.open("r", encoding="utf-8", errors="ignore") as fin, out_path.open(
        "w", encoding="utf-8"
    ) as fout:
        for line in fin:
            stripped = line.strip()
            if not stripped or stripped.startswith("#"):
                fout.write(line)
                continue
            toks = stripped.split()
            try:
                rid = int(float(toks[0]))
            except Exception:
                fout.write(line)
                continue

            if rid in hidden_set:
                if len(toks) >= 4:
                    fout.write(f"{rid} {toks[1]} {toks[2]} {toks[3]} 0.000\n")
                else:
                    fout.write(line)
                continue

            if rid in palette:
                r, g, b, a = palette[rid]
                fout.write(f"{rid} {r:.6f} {g:.6f} {b:.6f} {a:.3f}\n")
            else:
                fout.write(line)
    return out_path


def resolve_visual_color_file(
    color_file: Path,
    material_file: Path,
    outdir: Path,
    id_to_name: Dict[int, str],
    vis_only_keywords: List[str],
    vis_hide_keywords: List[str],
    distinct_colors: bool = False,
) -> Path:
    hide_ids: List[int] = []
    if vis_only_keywords:
        _, keep_vis_ids, _ = load_material_table_and_select(material_file, list(vis_only_keywords))
        keep_vis_set = {int(x) for x in keep_vis_ids}
        hide_ids = [int(rid) for rid in id_to_name.keys() if int(rid) not in keep_vis_set]
    elif vis_hide_keywords:
        _, hide_ids, _ = load_material_table_and_select(material_file, list(vis_hide_keywords))

    if distinct_colors:
        distinct_file = create_distinct_colour_file(
            color_file,
            outdir,
            id_to_name,
            hidden_ids=hide_ids,
        )
        print(
            f"[INFO] distinct vis colour file: {distinct_file} "
            f"(hidden_regions={len(hide_ids)})"
        )
        return distinct_file

    if not hide_ids:
        return color_file

    hidden_color_file = create_hidden_only_colour_file(color_file, outdir, hidden_ids=hide_ids)
    print(
        f"[INFO] hidden-only vis colour file: {hidden_color_file} "
        f"(hidden_regions={len(hide_ids)})"
    )
    return hidden_color_file


def make_common_dose_actor(
    sim,
    name: str,
    attached_to,
    grid_size: List[int],
    spacing: List[float],
    translation: List[float],
    output_basename: str,
    config: Dict,
):
    actor = sim.add_actor("DoseActor", name)
    actor.attached_to = attached_to
    actor.write_to_disk = bool(config.get("write_to_disk", True))
    try_set(actor, "size", grid_size)
    try_set(actor, "spacing", spacing)
    try_set(actor, "translation", translation)
    try_set(actor, "hit_type", config.get("hit_type", "random"))

    output_coordinate_system = config.get("output_coordinate_system")
    if output_coordinate_system:
        try_set(actor, "output_coordinate_system", output_coordinate_system)

    actor.edep.output_filename = f"{output_basename}_edep.mhd"

    if bool(config.get("enable_edep_uncertainty", False)):
        actor.edep_uncertainty.active = True
        actor.edep_uncertainty.output_filename = f"{output_basename}_edep_uncertainty.mhd"

    if bool(config.get("enable_dose_output", False)):
        actor.dose.active = True
        actor.dose.output_filename = f"{output_basename}_dose.mhd"

    if bool(config.get("enable_dose_uncertainty", False)):
        actor.dose_uncertainty.active = True
        actor.dose_uncertainty.output_filename = f"{output_basename}_dose_uncertainty.mhd"

    return actor
