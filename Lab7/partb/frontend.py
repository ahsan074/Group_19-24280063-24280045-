import streamlit as st
import subprocess
import time
import requests

# Function to start the FastAPI backend in the background
def start_backend():
    process = subprocess.Popen(
        ["uvicorn", "backend:app", "--host", "0.0.0.0", "--port", "8000"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )
    # Allow time for the backend to start
    time.sleep(3)
    return process

# Start the backend once when the app loads (using Streamlit session_state)
if "backend_process" not in st.session_state:
    st.session_state.backend_process = start_backend()

st.title("Iris Species Classifier")
st.write("Enter the measurements of an Iris flower to predict its species.")

# Input widgets for Iris features
sepal_length = st.number_input("Sepal Length (cm)", min_value=0.0, value=5.1)
sepal_width  = st.number_input("Sepal Width (cm)", min_value=0.0, value=3.5)
petal_length = st.number_input("Petal Length (cm)", min_value=0.0, value=1.4)
petal_width  = st.number_input("Petal Width (cm)", min_value=0.0, value=0.2)

if st.button("Predict"):
    payload = {
        "sepal_length": sepal_length,
        "sepal_width": sepal_width,
        "petal_length": petal_length,
        "petal_width": petal_width
    }
    try:
        # Call the FastAPI endpoint running on localhost:8000
        response = requests.post("http://localhost:8000/predict", json=payload)
        if response.status_code == 200:
            result = response.json()
            st.success(f"Predicted Iris species: **{result['prediction']}**")
        else:
            st.error("Error in prediction API.")
    except Exception as e:
        st.error(f"Error: {e}")

