

Go in data/test099_pytomo/data


        voxelize_iec_phantom -s 1 -o iec_1mm.mhd --output_source iec_activity_1mm.mhd -a 1 1 1 1 1 1
        voxelize_iec_phantom -s 2.4 -o iec_2.4mm.mhd --output_source iec_activity_2.4mm.mhd -a 1 1 1 1 1 1
        voxelize_iec_phantom -s 4.8 -o iec_4.8mm.mhd --output_source iec_activity_4.8mm.mhd -a 1 1 1 1 1 1 --no_shell

        opengate_photon_attenuation_image -i iec_1mm.mhd -o iec_mu_208kev_1mm.mhd -l iec_1mm_labels.json -e 0.208  --mdb iec_2.4mm.db -v
        opengate_photon_attenuation_image -i iec_4.8mm.mhd -o iec_mu_208kev_4.8mm.mhd -l iec_4.8mm_labels.json -e 0.208  --mdb iec_4.8mm.db -v