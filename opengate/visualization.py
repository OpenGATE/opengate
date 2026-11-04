"""Opt-in VTK visualisation driver for opengate.

Why a VTK driver
----------------
The Geant4 viewers are not a maintenance-free option for us: the image-volume
slices are drawn with fixed-function OpenGL calls inside Geant4's GL scene
handler (``core/opengate_core/opengate_lib/GateImageBox.cpp``), which needs a
private Geant4 header and is deprecated since macOS 10.14 (#1040, #800).  VTK
owns that problem for us: it is an actively maintained rendering toolkit, it
already has instancing/buffered pipelines and follows the GL->Vulkan/Metal
migration itself, and it is the rendering system the Geant4 developers point
to as the maintainable option (Geant4/geant4#122, #1175).

This module renders, with VTK only (no pyvista, no pyg4ometry), what GATE
already exports through the VRML scene handler: the geometry with its colours
and the trajectories, plus the image-volume slices that only the Qt viewer
shows today.  It is opt-in: ``sim.visu_type = "vtk"``.  A plain simulation
never imports VTK.

Hardware agnosticism
--------------------
Nothing here selects an OpenGL/Vulkan/Metal API by hand: VTK picks the best
one it was built with on the machine it runs on.  What this module adds is a
*capability probe* so the choice is reported and can be pinned:

    cuda   render on the NVIDIA proprietary driver (device choice, not an API)
    vulkan vtkWebGPURenderWindow with the Vulkan backend (Dawn)
    metal  vtkWebGPURenderWindow with the Metal backend (Dawn, macOS)
    gpu    the default VTK backend on whatever GPU is present
    cpu    software rendering (OSMesa / Mesa llvmpipe)

``resolve_backend("auto")`` walks that ladder, first success wins, and logs the
decision once, e.g.::

    visu backend: gpu -> OpenGL2 on AMD Radeon Pro 560X OpenGL Engine
    (skipped: cuda: no NVIDIA device; vulkan: VTK has no vtkWebGPURenderWindow)

An explicit backend never degrades silently, it raises ``VisuBackendError``
(the plan in discussion #1228).
"""

import json
import os
import subprocess
import sys
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path

from .logger import logger

# Preference order of the backend ladder (discussion #1228).
BACKENDS = ("cuda", "vulkan", "metal", "gpu", "cpu")

# The rungs that go through VTK's WebGPU module (Dawn), and the Dawn backend
# each one asks for: they are the only ones that need a VTK built with
# VTK_ENABLE_WEBGPU (the PyPI wheels are not).
_WEBGPU_RUNGS = {"vulkan": "Vulkan", "metal": "Metal"}

# Vendors/renderers that mean "this is not a GPU".
_SOFTWARE_MARKERS = (
    "llvmpipe",
    "softpipe",
    "swiftshader",
    "software rasterizer",
    "software renderer",
    "apple software renderer",
    "microsoft basic render driver",
    "gallium",
)

_INSTALL_HINT = (
    "The VTK visualisation needs the vtk package. Install it with:\n"
    "  pip install vtk\n"
    "or, to get the optional dependencies of opengate:\n"
    "  pip install 'opengate[vtk]'"
)


class VisuBackendError(RuntimeError):
    """Raised when the requested VTK backend (or VTK itself) is unavailable."""


@dataclass
class BackendInfo:
    """What the VTK render window will actually use."""

    requested: str = "auto"
    backend: str = ""  # rung of the ladder: cuda, vulkan, gpu or cpu
    api: str = ""  # concrete API: vulkan, opengl2, osmesa, ...
    vendor: str = ""
    renderer: str = ""
    version: str = ""
    device_index: int = -1  # pinned EGL/Vulkan device, -1 when not pinned
    skipped: dict = field(default_factory=dict)  # rung -> reason it was skipped
    render_ms: float = 0.0  # cost of the 32x32 probe frame
    blank: bool = False  # the probe frame read back empty (headless driver?)

    @property
    def software(self):
        r = (self.renderer + " " + self.vendor).lower()
        return any(m in r for m in _SOFTWARE_MARKERS)

    def summary(self):
        """The one-line decision that is logged, and that users paste in bug
        reports: ``gpu -> OpenGL2 on AMD Radeon Pro 560X OpenGL Engine``."""
        where = self.renderer or self.vendor or "unknown device"
        s = f"{self.backend} -> {self.api} on {where}"
        if self.blank:
            s += " (probe frame was blank)"
        return s

    def report(self):
        """The full decision, with the reason each earlier rung was skipped."""
        reasons = "; ".join(f"{k}: {v}" for k, v in self.skipped.items())
        return f"visu backend: {self.summary()}" + (
            f" (skipped: {reasons})" if reasons else ""
        )


class _RungUnavailable(Exception):
    """A rung of the ladder cannot even be tried on this machine."""


# -----------------------------------------------------------------------------
# VTK import: optional dependency, actionable message (#1175)
# -----------------------------------------------------------------------------
def import_vtk():
    """Import vtk, or raise VisuBackendError with the install command."""
    try:
        import vtk
    except Exception as exception:  # ImportError, or a broken vtk install
        raise VisuBackendError(f"{_INSTALL_HINT}\n\n(import error: {exception})")
    return vtk


# -----------------------------------------------------------------------------
# Capability probe
# -----------------------------------------------------------------------------
def _nvidia_devices():
    """Names of the NVIDIA devices of this machine, [] when there is none.

    This is a *device* question, not an API one: the cuda rung means "render on
    the NVIDIA proprietary driver", which is what a CUDA-capable driver
    provides.  It is deliberately checked on the actual system (and not on the
    machine the code was written on).
    """
    names = []

    # Linux: the proprietary driver exposes /dev/nvidia*
    if sys.platform.startswith("linux"):
        if Path("/dev").glob("nvidia*"):
            names += ["/dev/nvidia*"]
        for icd in (
            Path("/usr/share/vulkan/icd.d").glob("nvidia_icd.json")
            if Path("/usr/share/vulkan/icd.d").is_dir()
            else []
        ):
            names.append(str(icd))

    # nvidia-smi is the portable answer (Linux/Windows, and macOS on old Macs)
    try:
        out = subprocess.run(
            ["nvidia-smi", "--query-gpu=name", "--format=csv,noheader"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if out.returncode == 0:
            names += [n.strip() for n in out.stdout.splitlines() if n.strip()]
    except (OSError, subprocess.SubprocessError):
        pass

    return names


def _read_capabilities(window):
    """Vendor / renderer / version strings of the window, best effort."""
    vendor = renderer = version = ""
    try:
        caps = window.ReportCapabilities()
    except Exception:
        caps = ""
    for line in (caps or "").splitlines():
        line = line.strip()
        if line.lower().startswith("opengl vendor string:"):
            vendor = line.split(":", 1)[1].strip()
        elif line.lower().startswith("opengl renderer string:"):
            renderer = line.split(":", 1)[1].strip()
        elif line.lower().startswith("opengl version string:"):
            version = line.split(":", 1)[1].strip()
    if not renderer:
        # the WebGPU window reports an "Adapter" block instead of GL strings
        for line in (caps or "").splitlines():
            line = line.strip()
            key = line.split(":", 1)[0].strip().lower()
            if key in ("vendor", "name", "driver description", "architecture"):
                value = line.split(":", 1)[1].strip()
                if key == "vendor":
                    vendor = value
                elif key == "name":
                    renderer = value
                elif key == "driver description":
                    version = value
    if not renderer:
        try:
            renderer = window.GetClassName()
        except Exception:
            pass
    return vendor, renderer, version


# The concrete classes the factory would pick for OpenGL.  A VTK built with
# both modules hands out the WebGPU window for a plain vtkRenderWindow() (the
# factory preference does not override it on 9.7/macOS), so the OpenGL rungs
# have to name the window of their platform.
_GL_WINDOW_CLASSES = {
    "darwin": ("vtkCocoaRenderWindow",),
    "win32": ("vtkWin32OpenGLRenderWindow",),
}
_GL_WINDOW_CLASSES_LINUX = (
    "vtkXOpenGLRenderWindow",
    "vtkWaylandOpenGLRenderWindow",
)


def _gl_window(vtk):
    """The OpenGL render window of this platform, or a plain vtkRenderWindow."""
    names = _GL_WINDOW_CLASSES.get(sys.platform)
    if names is None:
        names = _GL_WINDOW_CLASSES_LINUX if sys.platform.startswith("linux") else ()
    for name in names:
        cls = getattr(vtk, name, None)
        if cls is not None:
            try:
                return cls()
            except Exception:
                continue
    return vtk.vtkRenderWindow()


def _gl_rung_window(vtk):
    """_gl_window(), refusing a VTK build whose factory is WebGPU-only.

    A build with both modules links RenderingOpenGL2, but its object factory
    hands out the WebGPU classes unconditionally (9.7/macOS ignores
    VTK_FACTORY_PREFER=RenderingBackend=OpenGL2), and mixing those mappers
    with an OpenGL window aborts the process.  Creating a mapper is the cheap
    way to know before a window is rendered.
    """
    window = _gl_window(vtk)
    if "webgpu" in window.GetClassName().lower():
        raise _RungUnavailable(
            "this VTK build has no OpenGL render window (WebGPU only): the "
            "gpu and cpu rungs need one built with RenderingOpenGL2"
        )
    try:
        mapper = vtk.vtkPolyDataMapper().GetClassName()
    except Exception:
        mapper = ""
    if "webgpu" in mapper.lower():
        raise _RungUnavailable(
            "this VTK build always creates the WebGPU classes (its object "
            "factory ignores RenderingBackend=OpenGL2), so its OpenGL path "
            "cannot be used: install the vtk wheel, or build VTK with "
            "WebGPU for the vtk-metal/vtk-vulkan rungs only"
        )
    return window


def _make_window(vtk, rung, nvidia):
    """A render window for one rung of the ladder, or _RungUnavailable.

    VTK picks the API; we only choose *which* window class, and (for cuda)
    which device it must run on.
    """
    device_index = -1

    if rung in _WEBGPU_RUNGS:
        cls = getattr(vtk, "vtkWebGPURenderWindow", None)
        if cls is None:
            raise _RungUnavailable(
                "VTK was not built with RenderingWebGPU (no vtkWebGPURenderWindow); "
                "the PyPI wheels are not, a build needs -DVTK_ENABLE_WEBGPU=ON"
            )
        # When both backends are linked, VTK's object factory prefers OpenGL2
        # unless told otherwise, and it reads that preference when the first
        # VTK object of the process is created (Rendering/WebGPU/README.md).
        # The probe therefore gives the WebGPU rungs their own child process;
        # setting it here only helps when this module is used directly.
        os.environ.setdefault("VTK_FACTORY_PREFER", "RenderingBackend=WebGPU")
        window = cls()
        config = window.GetWGPUConfiguration()
        if config is None:
            raise _RungUnavailable(
                "this vtkWebGPURenderWindow has no WGPU configuration"
            )
        wanted = _WEBGPU_RUNGS[rung]
        try:
            config.SetBackend(getattr(vtk.vtkWebGPUConfiguration.BackendType, wanted))
        except AttributeError:
            raise _RungUnavailable(
                f"this VTK has no vtkWebGPUConfiguration.BackendType.{wanted}"
            )
        # A backend with no adapter stalls for a minute by default (Dawn waits
        # for a device that will never come): the probe must not.
        try:
            config.SetTimeout(5000)
        except Exception:
            pass
        return window, wanted.lower(), device_index

    if rung == "cuda":
        if not nvidia:
            raise _RungUnavailable(
                "no NVIDIA device found (checked /dev/nvidia*, nvidia-smi)"
            )
        window = _gl_rung_window(vtk)
        # The device is *verified* after the first render, in _evaluate_rung:
        # the driver must report NVIDIA, otherwise this rung is refused.  That
        # is what catches the hybrid (Optimus/PRIME) case, where the default
        # GL device is the integrated GPU and calling it "the cuda path" would
        # be false.  Device pinning before the first render is not portable
        # (the EGL device list has no vendor names in VTK): on X11/GLX use
        # __NV_PRIME_RENDER_OFFLOAD=1 and __GLX_VENDOR_LIBRARY_NAME=nvidia, for
        # Vulkan point VK_ICD_FILENAMES at nvidia_icd.json, for EGL use
        # window.SetDeviceIndex() with the index of the NVIDIA device.
        try:
            if window.GetNumberOfDevices() == 1:
                window.SetDeviceIndex(0)
                device_index = 0
        except Exception:
            device_index = -1
        return window, "opengl2", device_index

    if rung == "cpu":
        # VTK only supports OSMesa on Linux (elsewhere the class exists but
        # aborts when it is rendered): only there is it worth constructing.
        cls = (
            getattr(vtk, "vtkOSOpenGLRenderWindow", None)
            if sys.platform.startswith("linux")
            else None
        )
        if cls is not None:
            try:
                return cls(), "osmesa", device_index
            except Exception:
                pass
        # llvmpipe is still reached through the OpenGL window; the vendor string
        # tells whether it is software, and _evaluate_rung checks that.
        return _gl_rung_window(vtk), "opengl2", device_index

    # gpu
    return _gl_rung_window(vtk), "opengl2", device_index


def _render_test(vtk, window):
    """Draw one 32x32 offscreen frame.  Returns (ms, blank, mapper class).

    The window is left initialised on purpose: ReportCapabilities() segfaults
    on some VTK builds (9.7/macOS) when it is called before the first render.
    The mapper class is what tells whether the WebGPU module is driving the
    render: VTK's WebGPU window reports neither GetRenderingBackend() (always
    "") nor always a ready device.
    """
    window.SetOffScreenRendering(1)
    window.SetSize(32, 32)
    renderer = vtk.vtkRenderer()
    renderer.SetBackground(0.0, 0.0, 0.0)
    window.AddRenderer(renderer)
    source = vtk.vtkSphereSource()
    source.SetThetaResolution(16)
    source.SetPhiResolution(16)
    mapper = vtk.vtkPolyDataMapper()
    mapper.SetInputConnection(source.GetOutputPort())
    actor = vtk.vtkActor()
    actor.SetMapper(mapper)
    renderer.AddActor(actor)
    renderer.ResetCamera()

    t0 = time.perf_counter()
    window.Render()
    ms = 1000.0 * (time.perf_counter() - t0)

    blank = True
    try:
        w2i = vtk.vtkWindowToImageFilter()
        w2i.SetInput(window)
        w2i.ReadFrontBufferOff()
        w2i.Update()
        image = w2i.GetOutput()
        scalars = image.GetPointData().GetScalars()
        if scalars is not None:
            from vtk.util.numpy_support import vtk_to_numpy

            blank = bool(vtk_to_numpy(scalars).max() == 0)
    except Exception:
        blank = False  # cannot read back: do not claim it is blank

    return ms, blank, mapper.GetClassName()


def _evaluate_rung(vtk, rung, nvidia):
    window, api, device_index = _make_window(vtk, rung, nvidia)

    # render first: ReportCapabilities() needs an initialised GL/Vulkan context
    ms, blank, mapper_class = _render_test(vtk, window)
    vendor, renderer, version = _read_capabilities(window)
    # the adapter type must be read while the device is alive: Finalize()
    # destroys it, and the configuration then reports Undefined
    in_use = ""
    if rung in _WEBGPU_RUNGS:
        try:
            config = window.GetWGPUConfiguration()
            in_use = (config.GetBackendInUseAsString() or "") if config else ""
        except Exception:
            in_use = ""
        if in_use.lower() == "undefined":
            in_use = ""
    try:
        window.Finalize()
    except Exception:
        pass

    if rung in _WEBGPU_RUNGS:
        # The window accepted the request; the driver must now confirm it.  The
        # proof is that the scene is drawn by the WebGPU module, plus the
        # adapter type Dawn reports when the device is ready (a backend the
        # build does not have never gets that far: the adapter request fails).
        wanted = _WEBGPU_RUNGS[rung]
        if "webgpu" not in (mapper_class or "").lower():
            raise _RungUnavailable(
                f"the WebGPU module is not driving the render (mappers are "
                f"'{mapper_class}'), so the {wanted} backend was not used"
            )
        if in_use and in_use.lower() != wanted.lower():
            raise _RungUnavailable(
                f"Dawn was asked for {wanted} and delivered {in_use}"
            )
        renderer = f"{in_use or wanted} via WebGPU"

    driver = (vendor + " " + renderer).lower()
    software = any(m in driver for m in _SOFTWARE_MARKERS)

    if rung == "gpu" and software:
        raise _RungUnavailable(f"only a software renderer is available ({renderer})")
    if rung == "cpu" and not software:
        # Some platforms accept a vtkOSOpenGLRenderWindow and then silently
        # fall back to the GPU (macOS without OSMesa): that is not the cpu rung.
        raise _RungUnavailable(
            f"no software renderer on this platform (got '{renderer}')"
        )
    if rung == "cuda" and "nvidia" not in driver:
        # We asked for the NVIDIA driver and cannot prove we got it.
        raise _RungUnavailable(
            f"the render window did not use the NVIDIA driver (got '{renderer}'); "
            "on a hybrid GPU, force it with __NV_PRIME_RENDER_OFFLOAD=1 and "
            "__GLX_VENDOR_LIBRARY_NAME=nvidia"
        )
    if "nouveau" in driver:
        # a GL driver for the same card, but far slower: never the cuda path
        raise _RungUnavailable(
            f"the NVIDIA card is driven by nouveau, not by the proprietary driver ({renderer})"
        )

    return BackendInfo(
        backend=rung,
        api=api,
        vendor=vendor,
        renderer=renderer,
        version=version,
        device_index=device_index,
        render_ms=ms,
        blank=blank,
    )


def probe_rendering(only=None):
    """Try each rung of the ladder in this process, return a list of reports.

    Each entry is a dict with ``backend``, ``available`` and either the
    BackendInfo fields or the ``reason`` it was skipped.  This is what
    ``opengate_visu --probe`` prints, and what the unit tests exercise.

    ``only`` restricts the rungs (a name, or a sequence of names): the probe
    gives the WebGPU rungs their own process, since VTK's backend preference
    can only be set before the first VTK object of a process exists.
    """
    vtk = import_vtk()
    nvidia = _nvidia_devices()
    reports = []
    if only is None:
        rungs = BACKENDS
    elif isinstance(only, str):
        rungs = (only,)
    else:
        rungs = tuple(only)
    # The OpenGL rungs first: asking for WebGPU sets VTK_FACTORY_PREFER, which
    # VTK reads once per process and never gives back, so a WebGPU rung would
    # turn every later rung into another WebGPU window.
    ordered = tuple(r for r in rungs if r not in _WEBGPU_RUNGS) + tuple(
        r for r in rungs if r in _WEBGPU_RUNGS
    )
    for rung in ordered:
        try:
            info = _evaluate_rung(vtk, rung, nvidia)
            entry = asdict(info)
            entry["available"] = True
        except _RungUnavailable as exception:
            entry = {"backend": rung, "available": False, "reason": str(exception)}
        except Exception as exception:  # a driver can fail in any way
            entry = {
                "backend": rung,
                "available": False,
                "reason": f"{type(exception).__name__}: {exception}",
            }
        entry["nvidia_devices"] = nvidia
        reports.append(entry)
    return sorted(reports, key=lambda report: rungs.index(report["backend"]))


_PROBE_PREFIX = "VISU_PROBE_JSON:"


def _probe_in_child(timeout=180):
    """Run the probe in child processes, one JSON line per rung.

    A graphics backend can abort the whole process (on VTK 9.7/macOS, the
    OSMesa rung does), and no try/except catches a segfault.  The child streams
    its results, so a crash only loses the rung that crashed, and never kills a
    simulation that has already run (#1228: "probe in a child process").

    Each WebGPU rung gets a child of its own, started with VTK_FACTORY_PREFER
    set: VTK reads that preference when the first VTK object of a process is
    created, so a process that has already rendered with OpenGL cannot switch
    to WebGPU, and two WebGPU backends cannot be tried in one process either.
    """
    reports = []
    for rung in BACKENDS:
        env = dict(os.environ)
        if rung in _WEBGPU_RUNGS:
            env["VTK_FACTORY_PREFER"] = "RenderingBackend=WebGPU"
        if rung == "cuda":
            group = ("cuda", "gpu")
        elif rung == "cpu":
            # a broken OSMesa aborts the process (VTK 9.7 on Linux as well as
            # macOS): probed alone, it cannot take the gpu result down with it
            group = ("cpu",)
        elif rung in _WEBGPU_RUNGS:
            group = (rung,)
        else:
            continue  # already covered by the cuda group
        code = (
            "import json\n"
            "from opengate.visualization import probe_rendering\n"
            f"for report in probe_rendering({list(group)!r}):\n"
            f"    print({_PROBE_PREFIX!r} + json.dumps(report), flush=True)\n"
        )
        try:
            process = subprocess.run(
                [sys.executable, "-c", code],
                capture_output=True,
                text=True,
                timeout=timeout,
                env=env,
            )
        except (OSError, subprocess.SubprocessError):
            continue
        for line in process.stdout.splitlines():
            if line.startswith(_PROBE_PREFIX):
                reports.append(json.loads(line[len(_PROBE_PREFIX) :]))
    seen = {report["backend"] for report in reports}
    for rung in BACKENDS:
        if rung not in seen:
            reports.append(
                {
                    "backend": rung,
                    "available": False,
                    "reason": "the probe process aborted while initialising this "
                    "backend (graphics driver crash)",
                }
            )
    return sorted(reports, key=lambda report: BACKENDS.index(report["backend"]))


def probe_backends():
    """The rung reports used by resolve_backend(): from a child process by
    default, in this process when OPENGATE_VISU_PROBE_INPROCESS is set."""
    if os.environ.get("OPENGATE_VISU_PROBE_INPROCESS"):
        return probe_rendering()
    try:
        return _probe_in_child()
    except Exception as exception:
        logger.warning(
            f"Cannot probe the graphics backends in a child process ({exception}), "
            f"probing in this process"
        )
        return probe_rendering()


_BACKEND_CACHE = {}


def resolve_backend(requested="auto", use_cache=True):
    """Resolve the requested backend to one that works, and log the decision.

    ``requested`` is "auto", "cuda", "vulkan", "gpu" or "cpu"; it defaults to
    the OPENGATE_VISU_BACKEND environment variable when that is set.  The
    result is cached per process: the probe is never run per frame.
    """
    requested = (requested or "").strip().lower()
    if not requested or requested == "auto":
        requested = (os.environ.get("OPENGATE_VISU_BACKEND") or "auto").strip().lower()
    if requested not in ("auto",) + BACKENDS:
        raise VisuBackendError(
            f"Unknown VTK backend '{requested}'. Choose one of: "
            + ", ".join(("auto",) + BACKENDS)
        )

    if use_cache and requested in _BACKEND_CACHE:
        return _BACKEND_CACHE[requested]

    reports = probe_backends()
    skipped = {r["backend"]: r.get("reason", "") for r in reports if not r["available"]}

    if requested == "auto":
        order = [r for r in reports if r["available"]]
    else:
        order = [r for r in reports if r["available"] and r["backend"] == requested]
        if not order:
            raise VisuBackendError(
                f"The VTK backend '{requested}' is not usable on this machine: "
                f"{skipped.get(requested, 'unknown reason')}.\n"
                f"Use the default 'auto' (or one of {', '.join(BACKENDS)}) to let "
                f"VTK choose."
            )

    if not order:
        raise VisuBackendError(
            "No VTK backend is usable on this machine (tried "
            + ", ".join(BACKENDS)
            + "): "
            + "; ".join(f"{k}: {v}" for k, v in skipped.items())
            + ".\nInstall a working GPU driver, or Mesa (llvmpipe) for software "
            "rendering, and run `opengate_visu --probe` to see what is missing."
        )

    chosen = dict(order[0])
    chosen.pop("available", None)
    chosen.pop("nvidia_devices", None)
    info = BackendInfo(
        requested=requested,
        **{
            k: chosen[k]
            for k in (
                "backend",
                "api",
                "vendor",
                "renderer",
                "version",
                "device_index",
                "render_ms",
                "blank",
            )
        },
    )
    info.skipped = {k: v for k, v in skipped.items() if k != info.backend}
    logger.info(info.report())

    if use_cache:
        _BACKEND_CACHE[requested] = info
    return info


# -----------------------------------------------------------------------------
# Image-volume slices
# -----------------------------------------------------------------------------
def _world_transform(volume):
    """(3x3 rotation, translation) mapping the local frame of the volume to the
    world frame, for its first placement."""
    from .geometry.utility import get_transform_world_to_local

    translations, rotations = get_transform_world_to_local(volume, 0)
    return rotations, translations


def write_slices(filename, simulation):
    """Save the image-volume slices shown by the Qt viewer into a .npz file.

    The slices are already computed in ``ImageVolume.construct_slices()`` (and
    windowed in [0, 1] with ``visu_window``): this only hands them to the VTK
    process, together with the world transform of each image box.  Returns the
    filename, or None when the simulation has no image volume.
    """
    import numpy as np

    arrays = {}
    volumes = []
    for volume in simulation.volume_manager.volumes.values():
        slices = getattr(volume, "slice_xy", None)
        if slices is None:
            continue
        try:
            rotation, translation = _world_transform(volume)
        except Exception as exception:
            logger.warning(
                f"Cannot compute the world transform of the image volume "
                f"'{volume.name}', its slices are not displayed in VTK: {exception}"
            )
            continue
        i = len(volumes)
        arrays[f"vol{i}_name"] = np.array(volume.name)
        arrays[f"vol{i}_size"] = np.asarray(volume.size_pix, dtype=int)
        arrays[f"vol{i}_half_size_mm"] = np.asarray(volume.half_size_mm, dtype=float)
        arrays[f"vol{i}_rotation"] = np.asarray(rotation, dtype=float)
        arrays[f"vol{i}_translation"] = np.asarray(translation, dtype=float)
        arrays[f"vol{i}_slice_xy"] = np.asarray(volume.slice_xy, dtype=float)
        arrays[f"vol{i}_slice_xz"] = np.asarray(volume.slice_xz, dtype=float)
        arrays[f"vol{i}_slice_yz"] = np.asarray(volume.slice_yz, dtype=float)
        volumes.append(volume.name)

    if not volumes:
        return None

    arrays["names"] = np.array(volumes)
    np.savez(filename, **arrays)
    return filename


def load_slices(filename):
    """Read back what write_slices() saved, as a list of dicts."""
    import numpy as np

    data = np.load(filename, allow_pickle=False)
    out = []
    for i in range(len(data["names"])):
        out.append(
            {
                "name": str(data[f"vol{i}_name"]),
                "size": data[f"vol{i}_size"],
                "half_size_mm": data[f"vol{i}_half_size_mm"],
                "rotation": data[f"vol{i}_rotation"],
                "translation": data[f"vol{i}_translation"],
                "slice_xy": data[f"vol{i}_slice_xy"],
                "slice_xz": data[f"vol{i}_slice_xz"],
                "slice_yz": data[f"vol{i}_slice_yz"],
            }
        )
    return out


def _matrix(vtk, rotation=None, translation=None):
    """A vtkMatrix4x4 from a 3x3 rotation and/or a translation."""
    m = vtk.vtkMatrix4x4()
    if rotation is not None:
        for i in range(3):
            for j in range(3):
                m.SetElement(i, j, float(rotation[i][j]))
    if translation is not None:
        for i in range(3):
            m.SetElement(i, 3, float(translation[i]))
    return m


def _compose(vtk, left, right):
    """The product of two vtkMatrix4x4 (VTK matrices do not support @)."""
    out = vtk.vtkMatrix4x4()
    vtk.vtkMatrix4x4.Multiply4x4(left, right, out)
    return out


def _slice_plane(kind, size, half_size_mm):
    """Image dimensions, spacing, local origin and 2D->3D matrix of one slice.

    Replicates what GateImageBox.cpp does with its GL textures: the slice spans
    the image box, nearest-neighbour sampling, the plane goes through the
    middle of the box.  ``size`` is (nx, ny, nz) and ``half_size_mm``
    (hx, hy, hz).
    """
    nx, ny, nz = (int(s) for s in size)
    hx, hy, hz = (float(h) for h in half_size_mm)
    sx, sy, sz = 2 * hx / nx, 2 * hy / ny, 2 * hz / nz

    if kind == "xy":  # rows: y, columns: x, plane at z = 0
        dims, spacing, origin = (
            (nx, ny, 1),
            (sx, sy, 1.0),
            (-hx + sx / 2, -hy + sy / 2, 0.0),
        )
        # columns: image X -> world X, image Y -> world Y, normal -> world Z
        rot = ((1, 0, 0), (0, 1, 0), (0, 0, 1))
    elif kind == "xz":  # rows: z, columns: x, plane at y = 0
        dims, spacing, origin = (
            (nx, nz, 1),
            (sx, sz, 1.0),
            (-hx + sx / 2, -hz + sz / 2, 0.0),
        )
        # image X -> world X, image Y -> world Z, normal -> -world Y
        rot = ((1, 0, 0), (0, 0, -1), (0, 1, 0))
    else:  # yz, rows: z, columns: y, plane at x = 0
        dims, spacing, origin = (
            (ny, nz, 1),
            (sy, sz, 1.0),
            (-hy + sy / 2, -hz + sz / 2, 0.0),
        )
        # image X -> world Y, image Y -> world Z, normal -> world X
        rot = ((0, 0, 1), (1, 0, 0), (0, 1, 0))
    return dims, spacing, origin, rot


def add_slices(renderer, slices, outline_color=(0.5, 0.5, 0.5)):
    """Add the three middle slices of each image volume to a VTK renderer."""
    import numpy as np

    vtk = import_vtk()
    count = 0
    for volume in slices:
        rotation_world = volume["rotation"]
        translation_world = volume["translation"]

        for kind in ("xy", "xz", "yz"):
            data = np.asarray(volume[f"slice_{kind}"], dtype=np.float32)
            dims, spacing, origin, plane = _slice_plane(
                kind, volume["size"], volume["half_size_mm"]
            )
            if data.size != dims[0] * dims[1]:
                logger.warning(
                    f"Skipping the {kind} slice of the image volume "
                    f"'{volume['name']}': it has {data.size} pixels instead of "
                    f"{dims[0] * dims[1]}"
                )
                continue

            from vtk.util.numpy_support import numpy_to_vtk

            image = vtk.vtkImageData()
            image.SetDimensions(*dims)
            image.SetSpacing(*spacing)
            image.SetOrigin(*origin)
            # the slices are windowed in [0, 1] (ImageVolume.visu_window)
            scalars = numpy_to_vtk(np.ascontiguousarray(data).reshape(-1), deep=1)
            scalars.SetNumberOfComponents(1)
            image.GetPointData().SetScalars(scalars)

            if "webgpu" in renderer.GetClassName().lower():
                # The WebGPU module implements neither vtkImageSliceMapper nor
                # vtkImageActor (VTK 9.7), and an OpenGL image actor cannot
                # take a WebGPU mapper.  A textured plane uses the classes
                # that are implemented on both paths; the slice data is
                # already windowed in [0, 1], so a greyscale lookup table
                # reproduces what the GL path shows with window/level.  That
                # path has no nearest-neighbour sampling, so slices are
                # interpolated there.
                ha, hb = _outline_half_sizes(kind, volume["half_size_mm"])
                quad = vtk.vtkPlaneSource()
                quad.SetOrigin(-ha, -hb, 0.0)
                quad.SetPoint1(ha, -hb, 0.0)
                quad.SetPoint2(-ha, hb, 0.0)
                mapper = vtk.vtkPolyDataMapper()
                mapper.SetInputConnection(quad.GetOutputPort())
                texture = vtk.vtkTexture()
                texture.SetInputData(image)
                texture.SetLookupTable(_greyscale_lut(vtk))
                actor = vtk.vtkActor()
                actor.SetMapper(mapper)
                actor.SetTexture(texture)
            else:
                mapper = vtk.vtkImageSliceMapper()
                mapper.SetInputData(image)
                mapper.SetOrientationToZ()

                actor = vtk.vtkImageSlice()
                actor.SetMapper(mapper)
                actor.GetProperty().SetInterpolationTypeToNearest()
                actor.GetProperty().SetColorWindow(1.0)
                actor.GetProperty().SetColorLevel(0.5)
            # local frame of the box -> world
            to_world = _compose(
                vtk,
                _matrix(vtk, rotation_world, translation_world),
                _matrix(vtk, plane),
            )
            actor.SetUserMatrix(to_world)
            renderer.AddViewProp(actor)

            # the grey outline of the slice (GateImageBox draws a LINE_LOOP)
            ha, hb = _outline_half_sizes(kind, volume["half_size_mm"])
            points = vtk.vtkPoints()
            for a, b in ((-ha, -hb), (ha, -hb), (ha, hb), (-ha, hb)):
                points.InsertNextPoint(a, b, 0.0)
            lines = vtk.vtkCellArray()
            lines.InsertNextCell(5)
            for index in (0, 1, 2, 3, 0):
                lines.InsertCellPoint(index)
            polydata = vtk.vtkPolyData()
            polydata.SetPoints(points)
            polydata.SetLines(lines)
            mapper_line = vtk.vtkPolyDataMapper()
            mapper_line.SetInputData(polydata)
            outline = vtk.vtkActor()
            outline.SetMapper(mapper_line)
            outline.GetProperty().SetColor(*outline_color)
            outline.GetProperty().SetLineWidth(1.0)
            outline.SetUserMatrix(to_world)
            renderer.AddViewProp(outline)
            count += 1
    return count


def _greyscale_lut(vtk):
    """A 256-entry black-to-white lookup table over [0, 1] (slice textures)."""
    lut = vtk.vtkLookupTable()
    lut.SetNumberOfTableValues(256)
    lut.SetRange(0.0, 1.0)
    lut.Build()
    for i in range(256):
        value = i / 255.0
        lut.SetTableValue(i, value, value, value, 1.0)
    return lut


def _outline_half_sizes(kind, half_size_mm):
    hx, hy, hz = (float(h) for h in half_size_mm)
    if kind == "xy":
        return hx, hy
    if kind == "xz":
        return hx, hz
    return hy, hz


# -----------------------------------------------------------------------------
# Scene
# -----------------------------------------------------------------------------
def add_axes(renderer, length=500.0, interactor=None):
    """The orientation axes of the Qt viewer (``/vis/scene/add/axes 0 0 0 50 cm``)."""
    vtk = import_vtk()
    axes = vtk.vtkAxesActor()
    axes.SetTotalLength(length, length, length)
    axes.SetShaftTypeToCylinder()
    axes.SetCylinderRadius(0.01)
    axes.SetConeRadius(0.05)
    axes.SetNormalizedLabelPosition(1.05, 1.05, 1.05)
    if interactor is not None:
        widget = vtk.vtkOrientationMarkerWidget()
        widget.SetOrientationMarker(axes)
        widget.SetInteractor(interactor)
        widget.SetViewport(0.0, 0.0, 0.15, 0.25)
        widget.SetEnabled(1)
        widget.InteractiveOff()
        return widget
    renderer.AddActor(axes)
    return axes


def import_vrml(window, filename, edges=False):
    """Import a VRML scene (geometry, colours, trajectories) into ``window``.

    GATE's VRML2FILE export carries everything the Qt and VRML viewers display:
    the volumes with their colours and the accumulated trajectories.  The VTK
    importer turns them into actors and brings its own renderer, which it
    attaches to the window: that renderer is returned, and is the one to add
    the slices and the axes to.
    """
    vtk = import_vtk()
    path = Path(filename)
    if not path.is_file():
        raise VisuBackendError(f"The visualisation file '{path}' does not exist")

    importer = vtk.vtkVRMLImporter()
    importer.SetFileName(str(path))
    importer.SetRenderWindow(window)
    # VTK >= 9.6 moved the parsing to the vtkImporter API (Update()); older
    # versions (9.3-9.5) expose Read().
    if hasattr(importer, "Update"):
        importer.Update()
    else:
        importer.Read()
    renderer = importer.GetRenderer()
    if renderer is None:
        raise VisuBackendError(f"Cannot import the VRML scene '{path}'")

    if edges:
        # /vis/viewer/set/auxiliaryEdge true, as in default_visu_commands_qt.mac
        for prop in _props(renderer):
            if hasattr(prop, "GetProperty"):
                prop.GetProperty().EdgeVisibilityOn()
    return importer, renderer


def _props(renderer):
    props = []
    for i in range(renderer.GetViewProps().GetNumberOfItems()):
        props.append(renderer.GetViewProps().GetItemAsObject(i))
    return props


def _write_screenshot(vtk, window, filename):
    path = Path(filename)
    path.parent.mkdir(parents=True, exist_ok=True)
    suffix = path.suffix.lower()
    extension, writer_cls = {
        ".png": ("png", vtk.vtkPNGWriter),
        ".jpg": ("jpg", vtk.vtkJPEGWriter),
        ".jpeg": ("jpg", vtk.vtkJPEGWriter),
        ".tif": ("tif", vtk.vtkTIFFWriter),
        ".tiff": ("tif", vtk.vtkTIFFWriter),
    }.get(suffix, ("png", vtk.vtkPNGWriter))

    w2i = vtk.vtkWindowToImageFilter()
    w2i.SetInput(window)
    w2i.SetScale(1)
    w2i.ReadFrontBufferOff()
    w2i.Update()
    writer = writer_cls()
    writer.SetFileName(str(path.with_suffix(path.suffix or "." + extension)))
    writer.SetInputConnection(w2i.GetOutputPort())
    writer.Write()
    return str(path)


def _has_display():
    if sys.platform in ("darwin", "win32"):
        return True
    return bool(os.environ.get("DISPLAY") or os.environ.get("WAYLAND_DISPLAY"))


def build_scene(
    filename,
    *,
    backend="auto",
    slices=None,
    offscreen=True,
    size=(1024, 768),
    axes=True,
    axes_length=500.0,
    background=(0.0, 0.0, 0.0),
    edges=False,
    title="opengate",
):
    """Create the render window and renderer of a scene, without rendering it.

    Returns ``(info, window, renderer)``; the caller renders (and can time it),
    which is what the benchmark does.
    """
    vtk = import_vtk()
    info = resolve_backend(backend)
    window = _create_window(vtk, info)
    window.SetWindowName(title)
    window.SetSize(int(size[0]), int(size[1]))
    if offscreen:
        window.SetOffScreenRendering(1)

    importer, renderer = import_vrml(window, filename, edges=edges)
    renderer.SetBackground(*background)
    if slices is not None:
        add_slices(renderer, load_slices(slices))
    if axes:
        add_axes(renderer, length=axes_length)

    renderer.ResetCamera()
    renderer.GetActiveCamera().Azimuth(30)
    renderer.GetActiveCamera().Elevation(20)
    renderer.ResetCameraClippingRange()
    return info, window, renderer


def show(
    filename,
    *,
    backend="auto",
    slices=None,
    offscreen=None,
    screenshot=None,
    size=(1024, 768),
    axes=True,
    axes_length=500.0,
    background=(0.0, 0.0, 0.0),
    edges=False,
    interactive=None,
    title="opengate",
):
    """Display a VRML scene (plus optional image slices) in a VTK window.

    Parameters
    ----------
    filename : str | Path
        The VRML (``.wrl``) file exported by Geant4.
    backend : str
        "auto" (default), or one of "cuda", "vulkan", "metal", "gpu",
        "cpu".  An explicit backend raises when it cannot be used: no silent
        downgrade.
    slices : str | Path | None
        The ``.npz`` file written by :func:`write_slices` (image-volume slices).
    offscreen : bool | None
        Render without a window.  Defaults to True when a ``screenshot`` is
        requested or when there is no display (cluster, CI).
    screenshot : str | Path | None
        Save the rendered scene to this image (png, jpg, tiff).
    interactive : bool | None
        Start the interaction loop.  Defaults to ``not offscreen``.

    Returns
    -------
    BackendInfo
        The backend and device that were actually used.
    """
    vtk = import_vtk()
    if offscreen is None:
        offscreen = screenshot is not None or not _has_display()
    if interactive is None:
        interactive = not offscreen

    info, window, renderer = build_scene(
        filename,
        backend=backend,
        slices=slices,
        offscreen=offscreen,
        size=size,
        axes=False,  # the axes need the interactor when there is one
        axes_length=axes_length,
        background=background,
        edges=edges,
        title=title,
    )

    interactor = None
    if interactive:
        interactor = vtk.vtkRenderWindowInteractor()
        interactor.SetRenderWindow(window)
        interactor.SetInteractorStyle(vtk.vtkInteractorStyleTrackballCamera())
        window.SetInteractor(interactor)

    if axes:
        add_axes(renderer, length=axes_length, interactor=interactor)

    window.Render()

    if screenshot is not None:
        _write_screenshot(vtk, window, screenshot)

    if interactive:
        interactor.Initialize()
        interactor.Start()
    else:
        window.Finalize()

    return info


def _create_window(vtk, info):
    """The render window of a resolved backend, configured like the probe."""
    os.environ.setdefault(
        "VTK_FACTORY_PREFER",
        (
            "RenderingBackend=WebGPU"
            if info.backend in _WEBGPU_RUNGS
            else "RenderingBackend=OpenGL2"
        ),
    )
    if info.backend in _WEBGPU_RUNGS:
        window = vtk.vtkWebGPURenderWindow()
        config = window.GetWGPUConfiguration()
        if config is not None:
            config.SetBackend(
                getattr(
                    vtk.vtkWebGPUConfiguration.BackendType,
                    _WEBGPU_RUNGS[info.backend],
                )
            )
        return window
    if info.backend == "cpu" and info.api == "osmesa":
        cls = getattr(vtk, "vtkOSOpenGLRenderWindow", None)
        if cls is not None:
            return cls()
    window = _gl_window(vtk)
    if info.device_index >= 0:
        try:
            window.SetDeviceIndex(info.device_index)
        except Exception:
            pass
    return window


# -----------------------------------------------------------------------------
# Command line entry point (used by `opengate_visu --vtk` and for probes)
# -----------------------------------------------------------------------------
def main(argv=None):
    import argparse

    parser = argparse.ArgumentParser(description="opengate VTK visualisation driver")
    parser.add_argument("filename", nargs="?", help="VRML (.wrl) file to display")
    parser.add_argument(
        "--backend",
        "-b",
        default="auto",
        help="auto, cuda, vulkan, metal, gpu, cpu",
    )
    parser.add_argument("--slices", "-s", default=None, help=".npz image slices file")
    parser.add_argument(
        "--screenshot", "-o", default=None, help="save the scene to this image"
    )
    parser.add_argument(
        "--offscreen", action="store_true", help="render without a window"
    )
    parser.add_argument(
        "--probe", action="store_true", help="report the backend ladder and exit"
    )
    parser.add_argument("--json", action="store_true", help="with --probe: print JSON")
    args = parser.parse_args(argv)

    try:
        if args.probe:
            # in child processes: a graphics driver that aborts takes down the
            # rung that tried it, not the probe (and never the caller)
            reports = probe_backends()
            if args.json:
                print(json.dumps(reports, indent=2))
            else:
                for report in reports:
                    if report["available"]:
                        print(
                            f"{report['backend']:<7} ok    "
                            f"{report['api']} on {report['renderer']} "
                            f"({report['render_ms']:.0f} ms/probe frame)"
                        )
                    else:
                        print(f"{report['backend']:<7} n/a   {report['reason']}")
            return 0

        if not args.filename:
            parser.error("a VRML file is needed (or --probe)")
        info = show(
            args.filename,
            backend=args.backend,
            slices=args.slices,
            screenshot=args.screenshot,
            offscreen=args.offscreen or None,
        )
        print(info.report())
        return 0
    except VisuBackendError as exception:
        print(f"ERROR: {exception}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
