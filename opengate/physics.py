from xml.etree import ElementTree as ET

from box import Box

from enum import Enum
import xml.etree.ElementTree as ET

import opengate_core as g4

from .exception import warning, fatal
from .definitions import FLOAT_MAX
from .decorators import requires_fatal
from .base import GateObject, process_cls

from .utility import g4_units, get_material_name_variants

# names for particle cuts
cut_particle_names = {
    "gamma": "gamma",
    "electron": "e-",
    "positron": "e+",
    "proton": "proton",
}


# translation from particle names used in Gate
# to particles names used in Geant4
def translate_particle_name_gate_to_geant4(name):
    """Convenience function to translate from names
    used in Gate to those in G4, if necessary.
    Concerns e.g. 'electron' -> 'e-'
    """
    try:
        return cut_particle_names[name]
    except KeyError:
        return name


class UserLimitsPhysics(g4.G4VPhysicsConstructor):
    """
    Class to be registered to physics list.

    It is essentially a refined version of StepLimiterPhysics which considers the user's
    particles choice of particles to which the step limiter should be added.

    """

    def __init__(self):
        """Objects of this class are created via the PhysicsEngine class.
        The user should not create objects manually.

        """
        g4.G4VPhysicsConstructor.__init__(self, "UserLimitsPhysics")
        self.physics_engine = None

        self.g4_step_limiter_storage = {}
        self.g4_special_user_cuts_storage = {}

    def close(self):
        self.g4_step_limiter_storage = None
        self.g4_special_user_cuts_storage = None
        self.physics_engine = None

    @requires_fatal("physics_engine")
    def ConstructParticle(self):
        """Needs to be defined because C++ base class declares this as purely virtual member."""
        pass

    @requires_fatal("physics_engine")
    def ConstructProcess(self):
        """Overrides method from G4VPhysicsConstructor
        that is called when the physics list is constructed.

        """
        ui = self.physics_engine.user_info_physics_manager

        particle_keys_to_consider = []
        # 'all' overrides individual settings
        if ui.user_limits_particles["all"] is True:
            particle_keys_to_consider = list(ui.user_limits_particles.keys())
        else:
            keys_to_exclude = ("all", "all_charged")
            particle_keys_to_consider = [
                p
                for p, v in ui.user_limits_particles.items()
                if v is True and p not in keys_to_exclude
            ]

        if len(particle_keys_to_consider) == 0:
            self.physics_engine.simulation_engine.simulation.warn_user(
                "user_limits_particles is False for all particles. No tracking cuts will be applied. Use sim.physics_manager.set_user_limits_particles()."
            )

        # translate to Geant4 particle names
        particles_to_consider = [
            translate_particle_name_gate_to_geant4(k) for k in particle_keys_to_consider
        ]

        for particle in g4.G4ParticleTable.GetParticleTable().GetParticleList():
            add_step_limiter = False
            add_user_special_cuts = False
            p_name = str(particle.GetParticleName())

            if p_name in particles_to_consider:
                add_step_limiter = True
                add_user_special_cuts = True

            # this reproduces the logic of the Geant4's G4StepLimiterPhysics class
            if (
                ui.user_limits_particles["all_charged"] is True
                and particle.GetPDGCharge() != 0
            ):
                add_step_limiter = True

            if add_step_limiter is True or add_user_special_cuts is True:
                pm = particle.GetProcessManager()
                if add_step_limiter is True:
                    # G4StepLimiter for the max_step_size cut
                    g4_step_limiter = g4.G4StepLimiter("StepLimiter")
                    pm.AddDiscreteProcess(g4_step_limiter, 1)
                    # store limiter and cuts in lists to
                    # to avoid garbage collection after exiting the methods
                    self.g4_step_limiter_storage[p_name] = g4_step_limiter
                if add_user_special_cuts is True:
                    # G4UserSpecialCuts for the other cuts
                    g4_user_special_cuts = g4.G4UserSpecialCuts("UserSpecialCut")
                    pm.AddDiscreteProcess(g4_user_special_cuts, 1)
                    self.g4_special_user_cuts_storage[p_name] = g4_user_special_cuts


class Region(GateObject):
    """FIXME: Documentation of the Region class."""

    user_info_defaults = {}
    user_info_defaults["user_limits"] = (
        Box(
            {
                "max_step_size": None,
                "max_track_length": None,
                "min_ekine": None,
                "max_time": None,
                "min_range": None,
            }
        ),
        {
            "doc": "\tUser limits to be applied during tracking. \n"
            + "\tFIXME: Will be applied to all particles specified in the \n"
            + "\tlist under the `particles` keyword, if eligible.\n"
            + "\tUse `all` to apply tracking limits to all eligible particles.\n"
            + "\tThe following limits can be set:\n"
            + "\t* max_step_size\n"
            + "\t* max_track_length\n"
            + "\t* min_ekine\n"
            + "\t* max_time\n"
            + "\t* min_range\n",
            # expose_items=True means that the user_limits are also accessible directly
            # via Region.max_step_size, not only via Region.user_limits.max_step_size
            # that's more convenient for the user
            "expose_items": True,
        },
    )
    user_info_defaults["production_cuts"] = (
        Box(dict([(p, None) for p in cut_particle_names.keys()])),
        {
            "doc": "\tProduction cut per particle to be applied in volumes associated with this region.\n"
            + "\tShould be provided as key:value pair as: `particle_name` (string) : `cut_value` (numerical)\n"
            + "\tThe following particle names are allowed:\n"
            + "".join([f"\t* {p}\n" for p in cut_particle_names])
        },
    )
    user_info_defaults["em_switches"] = (
        Box([("deex", None), ("auger", None), ("pixe", None)]),
        {
            "doc": "Switch on/off EM parameters in this region. "
            "If None, the corresponding value from the world region is used.",
            "expose_items": True,
        },
    )

    def __init__(self, *args, **kwargs) -> None:
        # references to upper hierarchy level
        super().__init__(*args, **kwargs)

        self.physics_engine = None

        # dictionaries to hold volumes to which this region is associated
        # self.volumes = {}
        self.root_logical_volumes = {}

        # g4_objects; will be created by resp. initialize_XXX() methods
        self.g4_region = None
        self.g4_user_limits = None
        self.g4_production_cuts = None

        # flags for private use
        self._g4_region_initialized = False
        self._g4_user_limits_initialized = False
        self._g4_production_cuts_initialized = False

    @property
    def physics_manager(self):
        return self.simulation.physics_manager

    def reset(self):
        super().__init__(name=self.name, simulation=self.simulation)
        self.root_logical_volumes = {}

    # this version will work when Volume inherits from GateObject
    # def associate_volume(self, volume):
    #     volume_name = volume.name
    #     if volume_name not in self.root_logical_volumes.keys():
    #         self.root_logical_volumes[volume_name] = volume
    #     else:
    #         fatal(f'This volume {volume_name} is already associated with this region.')

    def close(self):
        self.release_g4_references()
        self.physics_engine = None

    def release_g4_references(self):
        self.g4_region = None
        self.g4_user_limits = None
        self.g4_production_cuts = None

    def to_dictionary(self):
        d = super().to_dictionary()
        d["root_logical_volumes_names"] = list(self.root_logical_volumes.keys())
        return d

    def from_dictionary(self, d):
        self.reset()
        super().from_dictionary(d)
        for vname in d["root_logical_volumes_names"]:
            self.associate_volume(vname)

    def need_step_limiter(self):
        if self.user_info["user_limits"]["max_step_size"] is not None:
            return True
        else:
            return False

    def need_user_special_cut(self):
        if (
            self.user_info["user_limits"]["max_track_length"] is not None
            or self.user_info["user_limits"]["min_ekine"] is not None
            or self.user_info["user_limits"]["max_time"] is not None
            or self.user_info["user_limits"]["min_range"] is not None
        ):
            return True
        else:
            return False

    @requires_fatal("physics_manager")
    def associate_volume(self, volume):
        # Allow volume object to be passed and retrieve its name in that case
        try:
            volume_name = volume.name
        except AttributeError:
            volume_name = volume

        if volume_name in self.root_logical_volumes:
            fatal(f"This volume {volume_name} is already associated with this region.")
        self.root_logical_volumes[volume_name] = None
        self.physics_manager.volumes_regions_lut[volume_name] = self

    def dump_production_cuts(self):
        s = ""
        for pname, cut in self.production_cuts.items():
            if cut is not None:
                s += f"{pname}: {cut}\n"
        return s

    @requires_fatal("physics_engine")
    def initialize(self):
        """
        This method wraps around all initialization methods of this class.

        It should be called from the physics_engine,
        after setting the self.physics_engine attribute.
        """
        self.initialize_volume_dictionaries()
        self.initialize_g4_production_cuts()
        self.initialize_g4_user_limits()
        self.initialize_g4_region()

    # This method is currently necessary because the actual volume objects
    # are only created at some point during initialization
    @requires_fatal("physics_engine")
    def initialize_volume_dictionaries(self):
        if self.physics_engine is None:
            fatal("No physics_engine defined.")
        for vname in self.root_logical_volumes.keys():
            self.root_logical_volumes[vname] = (
                self.physics_engine.simulation_engine.volume_engine.get_volume(vname)
            )

    def initialize_g4_region(self):
        if self._g4_region_initialized is True:
            fatal("g4_region already initialized.")

        rs = g4.G4RegionStore.GetInstance()
        self.g4_region = rs.FindOrCreateRegion(self.user_info.name)

        if self.g4_user_limits is not None:
            self.g4_region.SetUserLimits(self.g4_user_limits)

        # if self.g4_production_cuts is not None:
        self.g4_region.SetProductionCuts(self.g4_production_cuts)

        for vol in self.root_logical_volumes.values():
            self.g4_region.AddRootLogicalVolume(vol.g4_logical_volume, True)
            vol.g4_logical_volume.SetRegion(self.g4_region)

        self._g4_region_initialized = True

    def initialize_g4_production_cuts(self):
        self.user_info = Box(self.user_info)

        if self._g4_production_cuts_initialized is True:
            fatal("g4_production_cuts already initialized.")
        if self.g4_production_cuts is None:
            self.g4_production_cuts = g4.G4ProductionCuts()

        # 'all' overrides individual cuts per particle
        try:
            cut_for_all = self.user_info["production_cuts"]["all"]
        except KeyError:
            cut_for_all = None
        if cut_for_all is not None:
            for pname in self.user_info["production_cuts"].keys():
                if pname == "all":
                    continue
                g4_pname = translate_particle_name_gate_to_geant4(pname)
                self.g4_production_cuts.SetProductionCut(cut_for_all, g4_pname)
        else:
            for pname, cut in self.user_info["production_cuts"].items():
                if pname == "all":
                    continue
                # translate to G4 names, e.g. electron -> e+
                g4_pname = translate_particle_name_gate_to_geant4(pname)
                if cut is not None:
                    self.g4_production_cuts.SetProductionCut(cut, g4_pname)
                # If no cut is specified by user for this particle,
                # set it to the value specified for the world region
                else:
                    global_cut = self.physics_engine.g4_physics_list.GetCutValue(
                        g4_pname
                    )
                    self.g4_production_cuts.SetProductionCut(global_cut, g4_pname)

        self._g4_production_cuts_initialized = True

    def initialize_g4_user_limits(self):
        if self._g4_user_limits_initialized is True:
            fatal("g4_user_limits already initialized.")

        # check if any user limits have been set
        # if not, it is not necessary to create g4 objects
        if all([(ul is None) for ul in self.user_info["user_limits"].values()]) is True:
            self._g4_user_limits_initialized = True
            return

        self.g4_user_limits = g4.G4UserLimits()

        if self.user_info["user_limits"]["max_step_size"] is None:
            self.g4_user_limits.SetMaxAllowedStep(FLOAT_MAX)
        else:
            self.g4_user_limits.SetMaxAllowedStep(
                self.user_info["user_limits"]["max_step_size"]
            )

        if self.user_info["user_limits"]["max_track_length"] is None:
            self.g4_user_limits.SetUserMaxTrackLength(FLOAT_MAX)
        else:
            self.g4_user_limits.SetUserMaxTrackLength(
                self.user_info["user_limits"]["max_track_length"]
            )

        if self.user_info["user_limits"]["max_time"] is None:
            self.g4_user_limits.SetUserMaxTime(FLOAT_MAX)
        else:
            self.g4_user_limits.SetUserMaxTime(
                self.user_info["user_limits"]["max_time"]
            )

        if self.user_info["user_limits"]["min_ekine"] is None:
            self.g4_user_limits.SetUserMinEkine(0.0)
        else:
            self.g4_user_limits.SetUserMinEkine(
                self.user_info["user_limits"]["min_ekine"]
            )

        if self.user_info["user_limits"]["min_range"] is None:
            self.g4_user_limits.SetUserMinRange(0.0)
        else:
            self.g4_user_limits.SetUserMinRange(
                self.user_info["user_limits"]["min_range"]
            )

        self._g4_user_limits_initialized = True

    def initialize_em_switches(self):
        # if all switches are None, nothing is to be set
        if any([v is not None for v in self.em_switches.values()]):
            values_to_set = {}
            for k, v in self.em_switches.items():
                if v is None:  # try to recover switch from world
                    values_to_set[k] = self.physics_manager.em_switches_world[k]
                    if values_to_set[k] is None:
                        fatal(
                            f"No value (True/False) provided for em_switch {k} in region {self.name} and no corresponding value set for the world either."
                        )
                else:
                    values_to_set[k] = v
            self.physics_engine.g4_em_parameters.SetDeexActiveRegion(
                self.name,
                values_to_set["deex"],
                values_to_set["auger"],
                values_to_set["pixe"],
            )


def get_enum_values(enum_class):
    # Filter out special Python attributes, methods, and pybind11 specific attributes
    return list(enum_class.__members__.keys())
    # return [
    #     attr
    #     for attr in dir(enum_class)
    #     if not attr.startswith("__")
    #        and not callable(getattr(enum_class, attr))
    #        and attr not in ["name", "value"]
    # ]


def load_optical_surface_properties_from_xml(surface_properties_file, surface_name):
    """
    This function extracts the information related to multiple surfaces
    from SurfaceProperties.xml
    """

    try:
        xml_tree = ET.parse(surface_properties_file)
    except FileNotFoundError:
        fatal(
            f"Could not find the surface_optical_properties_file {surface_properties_file}."
        )
    xml_root = xml_tree.getroot()

    found_surface_names = set()
    surface_properties = None
    for m in xml_root.findall("surface"):
        if m.get("name") == surface_name:
            surface_properties = {
                "base_properties": {
                    "surface_model": m.get("model"),
                    "surface_name": surface_name,
                    "surface_type": m.get("type"),
                    "surface_finish": m.get("finish"),
                    "surface_sigma_alpha": m.get("sigmaalpha"),
                },
                "constant_properties": {},
                "vector_properties": {},
            }

            # Handle propertyvector elements for UNIFIED Model
            for ptable in m.findall("propertiestable"):
                for prop_vector in ptable.findall("propertyvector"):
                    prop_vector_name = prop_vector.get("name")
                    prop_vector_value_unit = prop_vector.get("unit")
                    prop_vector_energy_unit = prop_vector.get("energyunit")

                    if prop_vector_value_unit is not None:
                        value_unit = g4_units[prop_vector_value_unit]
                    else:
                        value_unit = 1.0

                    if prop_vector_energy_unit is not None:
                        energy_unit = g4_units[prop_vector_energy_unit]
                    else:
                        energy_unit = 1.0

                    # Handle ve elements inside propertyvector
                    ve_energy_list = []
                    ve_value_list = []

                    for ve in prop_vector.findall("ve"):
                        ve_energy_list.append(float(ve.get("energy")) * energy_unit)
                        ve_value_list.append(float(ve.get("value")) * value_unit)

                    surface_properties["vector_properties"][prop_vector_name] = {
                        "prop_vector_value_unit": prop_vector_value_unit,
                        "prop_vector_energy_unit": prop_vector_energy_unit,
                        "ve_energy_list": ve_energy_list,
                        "ve_value_list": ve_value_list,
                    }

    if surface_properties is not None:
        return surface_properties
    else:
        fatal(
            f"No surface named {surface_name} not found in the XML file {surface_properties_file}"
        )


def load_optical_properties_from_xml(optical_properties_file, material_name):
    """This function parses an xml file containing optical material properties.
    Fetches property elements and property vector elements.

    Returns a dictionary with the properties or None if the material is not found in the file.
    """
    try:
        xml_tree = ET.parse(optical_properties_file)
    except FileNotFoundError:
        fatal(f"Could not find the optical_properties_file {optical_properties_file}.")
    xml_root = xml_tree.getroot()

    xml_entry_material = None
    for m in xml_root.findall("material"):
        # FIXME: some names might follow different conventions, e.g. 'Water' vs. 'G4_WATER'
        # using variants of the name is a possible solution, but this should be reviewed
        if str(m.get("name")) in get_material_name_variants(material_name):
            xml_entry_material = m
            break
    if xml_entry_material is None:
        warning(
            f"Could not find any optical material properties for material {material_name} "
            f"in file {optical_properties_file}."
        )
        return

    material_properties = {"constant_properties": {}, "vector_properties": {}}

    for ptable in xml_entry_material.findall("propertiestable"):
        # Handle property elements in XML document
        for prop in ptable.findall("property"):
            property_name = prop.get("name")
            property_value = float(prop.get("value"))
            property_unit = prop.get("unit")

            # apply unit if applicable
            if property_unit is not None:
                if len(property_unit.split("/")) == 2:
                    unit = property_unit.split("/")[1]
                else:
                    unit = property_unit
                property_value *= g4_units[unit]

            material_properties["constant_properties"][property_name] = {
                "property_value": property_value,
                "property_unit": property_unit,
            }

        # Handle propertyvector elements
        for prop_vector in ptable.findall("propertyvector"):
            prop_vector_name = prop_vector.get("name")
            prop_vector_value_unit = prop_vector.get("unit")
            prop_vector_energy_unit = prop_vector.get("energyunit")

            if prop_vector_value_unit is not None:
                value_unit = g4_units[prop_vector_value_unit]
            else:
                value_unit = 1.0

            if prop_vector_energy_unit is not None:
                energy_unit = g4_units[prop_vector.get("energyunit")]
            else:
                energy_unit = 1.0

            # Handle ve elements inside propertyvector
            ve_energy_list = []
            ve_value_list = []
            for ve in prop_vector.findall("ve"):
                ve_energy_list.append(float(ve.get("energy")) * energy_unit)
                ve_value_list.append(float(ve.get("value")) * value_unit)

            material_properties["vector_properties"][prop_vector_name] = {
                "prop_vector_value_unit": prop_vector_value_unit,
                "prop_vector_energy_unit": prop_vector_energy_unit,
                "ve_energy_list": ve_energy_list,
                "ve_value_list": ve_value_list,
            }

    return material_properties


def create_g4_optical_properties_table(material_properties_dictionary):
    """Creates and fills a G4MaterialPropertiesTable with values from a dictionary created by a parsing function,
    e.g. from an xml file.
    Returns G4MaterialPropertiesTable.
    """

    g4_material_table = g4.G4MaterialPropertiesTable()

    for property_name, data in material_properties_dictionary[
        "constant_properties"
    ].items():
        # check whether the property is already present
        create_new_key = (
            property_name not in g4_material_table.GetMaterialConstPropertyNames()
        )
        if create_new_key is True:
            warning(
                f"Found property {property_name} in optical properties file which is not known to Geant4. "
                f"I will create the property for you, but you should verify whether physics are correctly modeled."
            )
        g4_material_table.AddConstProperty(
            g4.G4String(property_name), data["property_value"], create_new_key
        )

    for property_name, data in material_properties_dictionary[
        "vector_properties"
    ].items():
        # check whether the property is already present
        create_new_key = (
            property_name not in g4_material_table.GetMaterialPropertyNames()
        )
        if create_new_key is True:
            warning(
                f"Found property {property_name} in optical properties file which is not known to Geant4. "
                f"I will create the property for you, but you should verify whether physics are correctly modeled."
            )
        g4_material_table.AddProperty(
            g4.G4String(property_name),
            data["ve_energy_list"],
            data["ve_value_list"],
            create_new_key,
            False,
        )

    return g4_material_table


class OpticalSurface(GateObject):
    """
    Class used to create an Optical Surface between two volumes

    G4OpticalSurface is used to create an optical surface

    G4LogicalBorderSurface is used to assign the optical surface
    between two volumes.
    """

    user_info_defaults = {
        "volume_from": (
            None,
            {
                "doc": "The volume from which photons propagate through the optical surface. "
            },
        ),
        "volume_to": (
            None,
            {
                "doc": "The volume into which the photons propagate coming from the surface. "
            },
        ),
        "g4_surface_name": (
            None,
            {
                "doc": "Name of the Geant4 surface to be created between volume_from and volume_to"
            },
        ),
    }

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)

        self.physics_engine = None

        # dictionary holding optical surface properties
        # populate from information stored in an external file
        # whose location is specified via physics_manager.surface_properties_file
        self.optical_surface_properties_dict = None

        # Store Geant4 Optical Surface object
        self.g4_optical_surface = None
        # Store Geant4 Logical Border Surface object
        self.g4_logical_border_surface = None
        # Store Geant4 object for material properties table
        self.g4_optical_surface_table = None

    # shortcut for convenience
    @property
    def physics_manager(self):
        if self.simulation is not None:
            return self.simulation.physics_manager
        else:
            return None

    def release_g4_references(self):
        self.g4_optical_surface = None
        self.g4_logical_border_surface = None
        self.g4_optical_surface_table = None

    def close(self):
        self.release_g4_references()
        self.physics_engine = None
        super().close()

    def reset(self):
        self.__init__(name=self.name, physics_manager=self.physics_manager)

    def __getstate__(self):
        return_dict = super().__getstate__()
        return_dict["g4_optical_surface"] = None
        return_dict["g4_logical_border_surface"] = None
        return_dict["g4_optical_surface_table"] = None
        return return_dict

    @requires_fatal("physics_engine")
    def initialize(self):
        # Create object of Geant4 Optical Surface
        self.g4_optical_surface = g4.G4OpticalSurface(g4.G4String(self.g4_surface_name))

        self.optical_surface_properties_dict = load_optical_surface_properties_from_xml(
            self.physics_manager.surface_properties_file,
            self.g4_surface_name,
        )

        # Set properties to create G4 Optical Surface object
        surface_base_properties = self.optical_surface_properties_dict[
            "base_properties"
        ]

        # Set model (eg. Unified, LUT_Davis)
        model_name = surface_base_properties["surface_model"]
        try:
            model = getattr(g4.G4OpticalSurfaceModel, model_name)
            self.g4_optical_surface.SetModel(model)
        except AttributeError:
            fatal(
                f"Unknown Model - {model_name} \n"
                f"Available models are {get_enum_values(g4.G4OpticalSurfaceModel)}"
            )

        # Set surface type
        surface_type_name = surface_base_properties["surface_type"]
        try:
            surface_type = getattr(g4.G4SurfaceType, surface_type_name)
            self.g4_optical_surface.SetType(surface_type)
        except AttributeError:
            fatal(
                f"Unknown Surface Type - {surface_type_name} \n"
                f"Available Surface Types are {get_enum_values(g4.G4SurfaceType)}"
            )

        # Set finish
        surface_finish_name = surface_base_properties["surface_finish"]
        try:
            surface_finish = getattr(
                g4.G4OpticalSurfaceFinish, surface_finish_name, None
            )
            self.g4_optical_surface.SetFinish(surface_finish)
        except AttributeError:
            fatal(
                f"Unknown Surface Finish - {surface_finish_name} \n"
                f"Available Surface Finishes are {get_enum_values(g4.G4OpticalSurfaceFinish)}"
            )

        # Set sigma alpha
        surface_sigma_alpha = surface_base_properties["surface_sigma_alpha"]

        if surface_sigma_alpha is not None:
            self.g4_optical_surface.SetSigmaAlpha(
                float(surface_sigma_alpha) * g4_units.deg
            )

        # Set surface properties table
        self.g4_optical_surface_table = create_g4_optical_properties_table(
            self.optical_surface_properties_dict
        )

        self.g4_optical_surface.SetMaterialPropertiesTable(
            self.g4_optical_surface_table
        )

        # Set the Optical Surface between two volumes
        # g4_physical_volumes (local variables are OK because
        # permanent references are stored inside the respective python Volume instances)
        g4_physical_volume_from = (
            self.physics_engine.simulation_engine.volume_engine.get_volume(
                self.volume_from
            ).get_g4_physical_volume(0)
        )

        g4_physical_volume_to = (
            self.physics_engine.simulation_engine.volume_engine.get_volume(
                self.volume_to
            ).get_g4_physical_volume(0)
        )

        self.g4_logical_border_surface = g4.G4LogicalBorderSurface(
            g4.G4String(self.g4_surface_name),
            g4_physical_volume_from,
            g4_physical_volume_to,
            self.g4_optical_surface,
        )


process_cls(Region)
process_cls(OpticalSurface)
