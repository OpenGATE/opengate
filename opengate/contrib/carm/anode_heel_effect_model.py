import numpy as np
import pandas as pd
import pathlib
import joblib
from scipy.interpolate import interp1d


# Function to generate phi_weights and phi_angles based on kvp (energy)
def get_phi_distribution(kvp):
    # Load the scaler and model
    current_path = pathlib.Path(__file__).parent.resolve()
    scaler = joblib.load(current_path / "gbr_scaler.pkl")
    gbr_model = joblib.load(current_path / "gbr_model.pkl")

    distances = np.arange(-9, 10, 1)
    phi_angles = np.arctan(distances / 70)

    # Create a DataFrame for prediction
    input_data = pd.DataFrame(
        {
            "Distance": distances,
            "Energy": kvp,
            "Theta": phi_angles,
            "ThetaDegrees": np.degrees(phi_angles),
        }
    )

    # Scale the input data
    input_data_scaled = scaler.transform(input_data)

    # Predict the weights
    phi_weights = gbr_model.predict(input_data_scaled)

    # Now interpolate between the predicted values with finer steps
    fine_distances = np.arange(-9, 9.01, 0.1)
    fine_phi_angles = np.arctan(fine_distances / 70)

    # Interpolate the predicted weights using linear interpolation
    interp_function = interp1d(distances, phi_weights, kind="linear")

    # Interpolate predictions for the finer distances
    fine_phi_weights = interp_function(fine_distances)
    fine_phi_weights = fine_phi_weights[1:]

    # Adjust angles (shift them by 90 degrees in radians)
    for i in range(len(fine_phi_angles)):
        fine_phi_angles[i] = fine_phi_angles[i] + 180 * np.pi / 180

    return fine_phi_weights, fine_phi_angles
