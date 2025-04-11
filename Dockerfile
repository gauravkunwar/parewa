# --- START OF FILE Dockerfile ---

# Use an official Python runtime as a parent image
FROM python:3.9-slim

# Set the working directory in the container
WORKDIR /app

# Copy the requirements file into the container at /app
COPY requirements.txt .

# Install any needed packages specified in requirements.txt
# --no-cache-dir keeps the image size smaller
# --trusted-host avoids potential SSL issues in some environments
RUN pip install --no-cache-dir --trusted-host pypi.python.org --trusted-host files.pythonhosted.org -r requirements.txt

# Copy the rest of the application code into the container at /app
# Ensure templates folder (if any) and app.py are copied
COPY . .

# Make port 5000 available to the world outside this container (Gunicorn will bind to this)
EXPOSE 5000

# Define environment variable placeholders (optional, mostly for documentation)
ENV FLASK_APP=app.py

# Run the application using Gunicorn when the container launches
# "app:app" means: In the file app.py, find the Flask object named 'app'.
# --bind 0.0.0.0:5000 makes Gunicorn listen on all interfaces inside the container on port 5000.
# --workers 2 is a starting point for concurrency. Adjust based on needs/resources.
CMD ["gunicorn", "--workers", "2", "--bind", "0.0.0.0:5000", "app:app"]

# --- END OF FILE Dockerfile ---