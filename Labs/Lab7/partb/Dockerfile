# Use a slim Python image as the base
FROM python:3.8-slim

# Set the working directory
WORKDIR /app

# Copy the requirements file and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy all source files into the container
COPY . .

# Expose port 8501 for Streamlit (the FastAPI runs on an internal port)
EXPOSE 8501

# Start the Streamlit app (which starts the backend as a subprocess)
CMD ["streamlit", "run", "frontend.py", "--server.port=8501", "--server.address=0.0.0.0"]
