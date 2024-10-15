#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import opengate as gate


def add_point_source(simulation, source_name, heads, rad, activity):
    mm = gate.g4_units.mm
    cm = gate.g4_units.cm

    source = simulation.add_source("GenericSource", source_name)
    source.particle = "gamma"
    gate.sources.generic.set_source_rad_energy_spectrum(source, rad)
    source.position.type = "sphere"
    source.position.radius = 1 * mm
    source.position.translation = [5 * cm, 0, 0]
    source.direction.type = "iso"
    source.direction.acceptance_angle.volumes = [h.name for h in heads]
    source.direction.acceptance_angle.skip_policy = "SkipEvents"
    source.direction.acceptance_angle.intersection_flag = True
    source.activity = activity

    return source
