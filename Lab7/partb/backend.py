from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import joblib
import numpy as np

app = FastAPI()

# Define the input data schema
class IrisInput(BaseModel):
    sepal_length: float
    sepal_width: float
    petal_length: float
    petal_width: float

# Load the pre-trained Iris model
model = joblib.load("iris_model.pkl")

# Define species mapping
species = {0: "setosa", 1: "versicolor", 2: "virginica"}

@app.post("/predict")
def predict(iris: IrisInput):
    try:
        # Prepare input for prediction
        features = np.array([[iris.sepal_length, iris.sepal_width, iris.petal_length, iris.petal_width]])
        pred = model.predict(features)
        return {"prediction": species[int(pred[0])]}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
