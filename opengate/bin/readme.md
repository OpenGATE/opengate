

# test dose_rate
cd contrib
dose_rate dose_rate_test1.json


# test voxelize
cd opengate
voxelize_iec_phantom -o data/iec_4mm.mhd -s 4

# phid

phid_atomic_relaxation i131 --from_data_file x_rays_detail.csv
phid_atomic_relaxation xe131 --from_data_file x_rays_detail.csv
