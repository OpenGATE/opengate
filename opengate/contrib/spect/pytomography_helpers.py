# if pytomography is not installed, we ignore this module
# this is needed for test080_check_classes_are_processed.py
# that check all modules
try:
    import pytomography
except ModuleNotFoundError:
    print("pytomography module is not installed. Skipping pytomography_helpers.")
    import sys

    # Unload this module to prevent errors in other imports
    sys.modules[__name__] = None
    raise SystemExit

import json
import torch
import warnings
import numpy as np
import SimpleITK as sitk
from pathlib import Path
from pytomography.metadata.SPECT import SPECTObjectMeta, SPECTProjMeta, SPECTPSFMeta
from pytomography.transforms.SPECT import SPECTPSFTransform, SPECTAttenuationTransform
from pytomography.projectors.SPECT import SPECTSystemMatrix
from pytomography.likelihoods import PoissonLogLikelihood
from pytomography.algorithms import OSEM


def convert_image_gate_to_pytomo(np_image):
    """
    Convert a numpy image to the pytomography coordinate system.
    => works in both direction (convert_image_pytomo_to_gate)
    """
    rotation_arr = np.transpose(np_image, axes=(2, 1, 0))
    rotation_arr = rotation_arr[:, ::-1, :].copy()
    return rotation_arr


def convert_image_pytomo_to_gate(np_image):
    """
    Convert a pytomography numpy image to the gate coordinate system.
    => works in both direction (convert_image_gate_to_pytomo)
    """
    rotation_arr = np.transpose(np_image, axes=(2, 1, 0))
    rotation_arr = rotation_arr[:, ::-1, :].copy()
    return rotation_arr


def convert_sinogram_gate_to_pytomo(np_sinogram):
    """
    Rotate numpy sinogram to the Pytomography coordinate system [angles,z,x] -> [angles,x,z]
    we reverse the Z axis (gantry rotation) because the rotation of the
    gantry is in the opposite direction
    """
    rotated_sinogram = np.transpose(np_sinogram, axes=(0, 2, 1))
    rotated_sinogram = rotated_sinogram[:, :, ::-1].copy()
    return rotated_sinogram


class _ConfigBlock:
    """Base class for parameter blocks to handle dict conversion."""

    def to_dict(self):
        # We only return public attributes
        return {k: v for k, v in vars(self).items() if not k.startswith("_")}

    def __str__(self):
        lines = [f"[{self.__class__.__name__}]"]
        for k, v in self.to_dict().items():
            if isinstance(v, np.ndarray):
                # Print arrays concisely (e.g., shape and a few elements)
                arr_str = np.array2string(v, precision=2, separator=", ", threshold=4)
                lines.append(f"  {k:<15}: {arr_str} (shape: {v.shape})")
            elif isinstance(v, list) and len(v) > 0 and isinstance(v[0], Path):
                # Format lists of paths cleanly
                lines.append(f"  {k:<15}: [")
                for p in v:
                    lines.append(f"    {p}")
                lines.append("  ]")
            else:
                lines.append(f"  {k:<15}: {v}")
        return "\n".join(lines)


class AcquisitionBlock(_ConfigBlock):
    def __init__(self):
        self.filenames = []
        self.angles = None
        self.radii = None
        self.size = None
        self.spacing = None
        self.num_channels = None
        self.index_peak = None
        self.isocenter = [0.0, 0.0, 0.0]

    def initialize_and_validate(self):
        if not self.filenames:
            raise ValueError("No acquisition filenames provided.")

        reader = sitk.ImageFileReader()
        reader.SetFileName(str(self.filenames[0]))
        reader.ReadImageInformation()

        proj_size = reader.GetSize()
        proj_spacing = reader.GetSpacing()

        # Auto-infer
        if getattr(self, "size", None) is None:
            self.size = [proj_size[0], proj_size[1]]
        if getattr(self, "spacing", None) is None:
            self.spacing = [proj_spacing[0], proj_spacing[1]]

        self.num_channels = len(self.filenames)

        if self.angles is not None and len(self.angles) != proj_size[2]:
            raise ValueError(
                f"Angles length ({len(self.angles)}) != projection depth ({proj_size[2]})."
            )

        if self.index_peak is None or self.index_peak is False:
            raise ValueError(
                f"Peak index ({self.index_peak}) must be a positive integer"
            )

        if self.index_peak < 0 or self.index_peak > self.num_channels:
            raise ValueError(
                f"Peak index ({self.index_peak}) out of range for number of channels ({self.num_channels}."
            )

        # Ensure isocenter is a 3D list/array
        self.isocenter = list(self.isocenter)
        if len(self.isocenter) != 3:
            raise ValueError(
                f"Isocenter must be a 3D coordinate, got: {self.isocenter}"
            )


class ReconstructionBlock(_ConfigBlock):
    def __init__(self):
        self.template_filename = None
        self.final_size = None
        self.final_spacing = None
        self.final_origin = None

    def initialize_and_validate(self):
        # Option A: User provided a reference image
        if self.template_filename is not None:
            reader = sitk.ImageFileReader()
            reader.SetFileName(str(self.template_filename))
            reader.ReadImageInformation()

            inferred_size = list(reader.GetSize())
            inferred_spacing = list(reader.GetSpacing())
            inferred_origin = list(reader.GetOrigin())

            # Warn if manual parameters were also set and conflict with the file
            if self.final_size is not None and list(self.final_size) != inferred_size:
                warnings.warn(
                    f"Overriding manual final_size {self.final_size} with reference file size {inferred_size}"
                )

            self.final_size = inferred_size
            self.final_spacing = inferred_spacing
            self.final_origin = inferred_origin

        # Option B: User provided explicit manual parameters
        else:
            if (
                self.final_size is None
                or self.final_spacing is None
                or self.final_origin is None
            ):
                raise ValueError(
                    "Reconstruction grid parameters are incomplete. "
                    "You must provide EITHER 'filename' OR all three of "
                    "('final_size', 'final_spacing', 'final_origin')."
                )

            # Coerce to standard lists for consistent JSON serialization downstream
            self.final_size = list(self.final_size)
            self.final_spacing = list(self.final_spacing)
            self.final_origin = list(self.final_origin)

            # Basic sanity check on the shapes
            if (
                len(self.final_size) != 3
                or len(self.final_spacing) != 3
                or len(self.final_origin) != 3
            ):
                raise ValueError(
                    "Reconstruction final_size, final_spacing, and final_origin must all be 3D lists or arrays."
                )


class MumapBlock(_ConfigBlock):
    def __init__(self):
        self.filename = None
        # start with "_" = computed
        self._size = None
        self._spacing = None
        self._origin = None

    def initialize_and_validate(self):
        if self.filename is not None:
            reader = sitk.ImageFileReader()
            reader.SetFileName(str(self.filename))
            reader.ReadImageInformation()

            # Store these temporarily/internally for the main adapter to check
            self._size = list(reader.GetSize())
            self._spacing = list(reader.GetSpacing())
            self._origin = list(reader.GetOrigin())

    def resample_like_working_grid(self, work_ref_img):
        mu_img = sitk.ReadImage(str(self.filename))

        # Resample Mumap to the strict Working Grid
        resampler = sitk.ResampleImageFilter()
        resampler.SetReferenceImage(work_ref_img)
        resampler.SetInterpolator(
            sitk.sitkLinear
        )  # Crucial for continuous attenuation values
        resampler.SetDefaultPixelValue(0.0)  # Air outside bounds
        mu_work = resampler.Execute(mu_img)

        mu_arr = sitk.GetArrayFromImage(mu_work)
        mu_arr_pt = convert_image_gate_to_pytomo(mu_arr)
        return mu_arr_pt


class PSFBlock(_ConfigBlock):
    def __init__(self):
        self.sigma_fit_params = None
        # String identifier (e.g., "3_param") or a callable.
        # Callables will trigger a warning on JSON dump.
        self.sigma_fit = None
        self.sigma_fit_fct = None

    def initialize_and_validate(self):
        if self.sigma_fit_params is not None:
            # Rehydrate the function if it's the standard string identifier
            if self.sigma_fit == "3_param":
                self.sigma_fit_fct = lambda r, a, b, c: np.sqrt((a * r + b) ** 2 + c**2)
            elif self.sigma_fit == "2_param":
                self.sigma_fit_fct = lambda r, a, b: a * r + b
            elif callable(self.sigma_fit):
                self.sigma_fit_fct = self.sigma_fit
            else:
                raise ValueError(f"Unknown PSF sigma_fit model: {self.sigma_fit}")


class ScatterCorrectionBlock(_ConfigBlock):
    def __init__(self):
        self.mode = None
        self.index_upper = None
        self.index_lower = None
        self.w_peak_kev = None
        self.w_lower_kev = None
        self.w_upper_kev = None


class AdapterEncoder(json.JSONEncoder):
    """Custom JSON encoder to handle NumPy arrays, Paths, and functions."""

    def default(self, obj):
        if isinstance(obj, np.ndarray):
            return obj.tolist()
        if isinstance(obj, Path):
            return str(obj)
        if callable(obj):
            warning_msg = (
                f"Custom function '{obj.__name__}' detected. It will not be serialized."
            )
            warnings.warn(warning_msg)
            return f"ERROR: <function {obj.__name__} (not serializable)>"
        if isinstance(obj, _ConfigBlock):
            return obj.to_dict()
        return super().default(obj)


class GateToPyTomographyAdapter:
    def __init__(self):
        self.acquisition = AcquisitionBlock()
        self.reconstruction = ReconstructionBlock()
        self.mumap = MumapBlock()
        self.psf = PSFBlock()
        self.scatter_correction = ScatterCorrectionBlock()

    def __str__(self):
        blocks = [
            self.acquisition,
            self.reconstruction,
            self.mumap,
            self.psf,
            self.scatter_correction,
        ]
        body = "\n\n".join(str(block) for block in blocks)

        return body

    def to_dict(self):
        """Converts the entire adapter state into a dictionary."""
        return {
            "acquisition": self.acquisition,
            "reconstruction": self.reconstruction,
            "mumap": self.mumap,
            "psf": self.psf,
            "scatter_correction": self.scatter_correction,
        }

    def dump(self, filepath):
        """Serializes the configuration to a JSON file."""
        filepath = Path(filepath)
        filepath.parent.mkdir(parents=True, exist_ok=True)

        with open(filepath, "w") as f:
            json.dump(self.to_dict(), f, indent=4, cls=AdapterEncoder)

    @classmethod
    def load(cls, filepath):
        """(Optional) Rehydrates the adapter from a JSON file."""
        filepath = Path(filepath)
        with open(filepath, "r") as f:
            data = json.load(f)

        adapter = cls()

        # Helper to safely map dictionaries back to block attributes
        def populate_block(block, data_dict):
            if not data_dict:
                return
            for k, v in data_dict.items():
                # Convert strings back to numpy arrays where expected
                if k in ["angles", "radii"] and v is not None:
                    setattr(block, k, np.array(v))
                # Convert path strings back to Path objects
                elif "filename" in k and v is not None:
                    if isinstance(v, list):
                        setattr(block, k, [Path(p) for p in v])
                    else:
                        setattr(block, k, Path(v))
                else:
                    setattr(block, k, v)

        populate_block(adapter.acquisition, data.get("acquisition"))
        populate_block(adapter.reconstruction, data.get("reconstruction"))
        populate_block(adapter.mumap, data.get("mumap"))
        populate_block(adapter.psf, data.get("psf"))
        populate_block(adapter.scatter_correction, data.get("scatter_correction"))

        return adapter

    def initialize_and_validate(self):
        """Triggers block validations and ensures global spatial consistency."""

        # 1. Initialize individual blocks
        self.acquisition.initialize_and_validate()
        self.reconstruction.initialize_and_validate()
        self.mumap.initialize_and_validate()
        self.psf.initialize_and_validate()
        # self.scatter_correction.initialize_and_validate()

        # 2. Cross-block validation: Mumap vs Reconstruction Grid
        if self.mumap.filename is not None:
            if (
                not np.allclose(
                    self.mumap._spacing, self.reconstruction.final_spacing, atol=1e-3
                )
                or not np.allclose(
                    self.mumap._origin, self.reconstruction.final_origin, atol=1e-3
                )
                or self.mumap._size != self.reconstruction.final_size
            ):
                warnings.warn(
                    "Mumap geometry (size, spacing, origin) does not strictly match the "
                    "reconstruction grid! This breaks sub-pixel alignment."
                )

    def reconstruct_osem(self, iterations=4, subsets=8, device="auto", verbose=False):
        """
        Executes the OSEM reconstruction using PyTomography.
        Enforces a strict Working Grid for physics accuracy and resamples to the Final Grid.
        """

        # ---------------------------------------------------------
        # 1. Device Setup
        # ---------------------------------------------------------
        if device == "auto":
            # Trust PyTomography's auto-detection (handles CUDA, MPS, and CPU)
            device = pytomography.device
        else:
            device = torch.device(device)
            # Synchronize PyTomography's global device with the user's choice
            pytomography.device = device
        verbose and print(f"Starting reconstruction on device: {device}")

        # need initialize before
        self.initialize_and_validate()

        # Enforce isotropic
        if self.acquisition.size[0] != self.acquisition.size[1]:
            raise ValueError(
                f"Acquisition size must be isotropic, "
                f"while it is {self.acquisition.size[0]}x{self.acquisition.size[1]}"
            )
        if self.acquisition.spacing[0] != self.acquisition.spacing[1]:
            raise ValueError(
                f"Acquisition spacing must be isotropic, "
                f"while it is {self.acquisition.spacing[0]}x{self.acquisition.spacing[1]}"
            )

        # ---------------------------------------------------------
        # 2. Define the Strict Working Grid (in mm for ITK)
        # ---------------------------------------------------------
        # Nx = Ny = size_u, Nz = size_v
        work_size = [
            self.acquisition.size[0],
            self.acquisition.size[0],
            self.acquisition.size[1],
        ]
        work_spacing = [
            self.acquisition.spacing[0],
            self.acquisition.spacing[0],
            self.acquisition.spacing[1],
        ]

        # Exact geometric center of the voxels, shifted by the physical isocenter
        work_origin = [
            -(work_size[0] - 1) * work_spacing[0] / 2.0 + self.acquisition.isocenter[0],
            -(work_size[1] - 1) * work_spacing[1] / 2.0 + self.acquisition.isocenter[1],
            -(work_size[2] - 1) * work_spacing[2] / 2.0 + self.acquisition.isocenter[2],
        ]

        # Create an empty ITK image to act as the spatial reference for the Working Grid
        work_ref_img = sitk.Image(work_size, sitk.sitkFloat32)
        work_ref_img.SetSpacing(work_spacing)
        work_ref_img.SetOrigin(work_origin)

        # ---------------------------------------------------------
        # 3. PyTomography Metadata Setup (Unit Conversion: mm -> cm)
        # ---------------------------------------------------------
        dr_cm = [work_spacing[0] / 10.0, work_spacing[1] / 10.0, work_spacing[2] / 10.0]
        object_meta = SPECTObjectMeta(dr=dr_cm, shape=work_size)

        proj_dr_cm = [
            self.acquisition.spacing[0] / 10.0,
            self.acquisition.spacing[1] / 10.0,
        ]
        proj_meta = SPECTProjMeta(
            projection_shape=(self.acquisition.size[0], self.acquisition.size[1]),
            dr=proj_dr_cm,
            angles=self.acquisition.angles,  # Assumed degrees
            radii=self.acquisition.radii / 10.0,  # convert to cm
        )

        # ---------------------------------------------------------
        # 4. Load & Rotate Sinograms
        # ---------------------------------------------------------
        sinograms_pt = []
        for filename in self.acquisition.filenames:
            img = sitk.ReadImage(str(filename))
            arr = sitk.GetArrayFromImage(img)
            # Apply PyTomography rotation: [Angles, Z, X] -> [Angles, X, Z] and Z flip
            arr_rotated = convert_sinogram_gate_to_pytomo(arr)
            sinograms_pt.append(
                torch.tensor(arr_rotated, dtype=torch.float32).to(device)
            )

        # ---------------------------------------------------------
        # 5. Build Object Transforms (Corrections)
        # ---------------------------------------------------------
        obj_transforms = []

        # -- Attenuation (Mumap) --
        if self.mumap.filename is not None:
            mu_arr_pt = self.mumap.resample_like_working_grid(work_ref_img)
            mu_tensor = torch.tensor(mu_arr_pt, dtype=torch.float32).to(device)
            att_transform = SPECTAttenuationTransform(mu_tensor)
            obj_transforms.append(att_transform)

        # -- Point Spread Function (PSF) --
        if self.psf.sigma_fit_params is not None:
            psf_meta = SPECTPSFMeta(
                sigma_fit_params=self.psf.sigma_fit_params,
                sigma_fit=self.psf.sigma_fit_fct,
            )
            psf_transform = SPECTPSFTransform(psf_meta)
            obj_transforms.append(psf_transform)

        # ---------------------------------------------------------
        # 6. Scatter Estimation
        # ---------------------------------------------------------
        additive_term = None
        if self.scatter_correction.mode == "TEW":
            from pytomography.utils import compute_EW_scatter

            p_lower = sinograms_pt[self.scatter_correction.index_lower]
            p_upper = sinograms_pt[self.scatter_correction.index_upper]

            # Actual width of the energy windows
            w_peak = self.scatter_correction.w_peak_kev
            w_lower = self.scatter_correction.w_lower_kev
            w_upper = self.scatter_correction.w_upper_kev

            additive_term = compute_EW_scatter(
                p_lower, p_upper, w_lower, w_upper, w_peak, proj_meta=proj_meta
            ).to(device)
        if self.scatter_correction.mode == "DEW":
            raise ValueError("DEW scatter correction is not supported yet.")

        # ---------------------------------------------------------
        # 7. System Matrix & Likelihood
        # ---------------------------------------------------------
        system_matrix = SPECTSystemMatrix(
            obj2obj_transforms=obj_transforms,
            proj2proj_transforms=[],
            object_meta=object_meta,
            proj_meta=proj_meta,
        )

        # The peak window index
        peak_idx = self.acquisition.index_peak
        print(f"Peak window index: {peak_idx} ({len(sinograms_pt)})")

        likelihood = PoissonLogLikelihood(
            system_matrix=system_matrix,
            projections=sinograms_pt[peak_idx],
            additive_term=additive_term,
        )

        # ---------------------------------------------------------
        # 8. OSEM Reconstruction
        # ---------------------------------------------------------
        verbose and print("Running OSEM...")
        recon_algorithm = OSEM(likelihood)
        recon_tensor = recon_algorithm(n_iters=iterations, n_subsets=subsets)

        # ---------------------------------------------------------
        # 9. Post-Processing: Rotate back and Resample
        # ---------------------------------------------------------
        recon_arr = recon_tensor.cpu().numpy()
        recon_arr = convert_image_pytomo_to_gate(recon_arr)

        # Convert to ITK in the Working Grid
        recon_img_work = sitk.GetImageFromArray(recon_arr)
        recon_img_work.SetSpacing(work_spacing)
        recon_img_work.SetOrigin(work_origin)

        # Define the Final Output Grid
        final_ref_img = sitk.Image(self.reconstruction.final_size, sitk.sitkFloat32)
        final_ref_img.SetSpacing(self.reconstruction.final_spacing)
        final_ref_img.SetOrigin(self.reconstruction.final_origin)

        # Calculate Volume Ratio to Preserve Counts
        work_vol = work_spacing[0] * work_spacing[1] * work_spacing[2]
        fin_sp = self.reconstruction.final_spacing
        final_vol = fin_sp[0] * fin_sp[1] * fin_sp[2]
        volume_ratio = final_vol / work_vol

        # Resample from Working Grid -> Final Grid
        verbose and print(
            f"Resampling to final grid (Volume scale factor: {volume_ratio:.4f})..."
        )
        final_resampler = sitk.ResampleImageFilter()
        final_resampler.SetReferenceImage(final_ref_img)
        final_resampler.SetInterpolator(sitk.sitkBSpline)
        final_resampler.SetDefaultPixelValue(0.0)
        recon_img_final = final_resampler.Execute(recon_img_work)

        # Apply the volume scale to conserve total counts
        recon_img_final = sitk.Multiply(recon_img_final, float(volume_ratio))

        # Clamp to remove negative ringing from spline interpolation
        recon_img_final = sitk.Clamp(recon_img_final, lowerBound=0.0)

        verbose and print("Reconstruction complete.")
        return recon_img_final
