# Use an official Python runtime as a parent image
FROM python:3.9-slim-buster

# Set the working directory in the container to /app
WORKDIR /app

# Add the current directory contents into the container at /app
ADD . /app

# Add the ENV path to /app
ENV PATH="/app:${PATH}"

# Install any needed packages specified in requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Test pip install
# RUN pip freeze

# Install ffmpeg and ffprobe
RUN apt-get update && apt-get install -y libmagic1 && rm -rf /var/lib/apt/lists/*

# Make port 5000 available to the world outside this container
EXPOSE 5000

# Run app.py when the container launches
CMD ["/bin/sh", "-c", "python app.py 2>&1"]
# CMD ["gunicorn", "app:app", "--worker-class", "gevent", "--bind", "0.0.0.0:5000"]