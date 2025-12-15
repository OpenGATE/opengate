import uproot

case = "neutron"

# Open the source ROOT file (data_merge_neutron.root) and extract the histogram
input_A = uproot.open("data/data_" + case + "_A.root")
input_B = uproot.open("data/data_" + case + "_B.root")

# Create a new ROOT file with the updated histogram
with uproot.recreate("data/data_merge_" + case + ".root") as new_file:
    for key, obj in input_A.items():
        # Remove the first ";1" from the key name
        clean_key = key.split(";")[0]  # Remove the cycle suffix
        if isinstance(obj, uproot.models.TH.Model_TH2D_v4):
            # Copy other TH2D histograms as they are
            bin_contents = obj.values()
            edges_x = obj.axis(0).edges()
            edges_y = obj.axis(1).edges()
            new_file[key] = (bin_contents, (edges_x, edges_y))
        elif isinstance(obj, uproot.models.TH.Model_TH1D_v3):
            # Handle TH1D histograms
            bin_contents = obj.values()
            edges_x = obj.axis(0).edges()
            new_file[key] = (bin_contents, edges_x)
    for key, obj in input_B.items():
        # Remove the first ";1" from the key name
        clean_key = key.split(";")[0]  # Remove the cycle suffix
        if isinstance(obj, uproot.models.TH.Model_TH2D_v4):
            # Copy other TH2D histograms as they are
            bin_contents = obj.values()
            edges_x = obj.axis(0).edges()
            edges_y = obj.axis(1).edges()
            new_file[key] = (bin_contents, (edges_x, edges_y))
        elif isinstance(obj, uproot.models.TH.Model_TH1D_v3):
            # Handle TH1D histograms
            bin_contents = obj.values()
            edges_x = obj.axis(0).edges()
            new_file[key] = (bin_contents, edges_x)
