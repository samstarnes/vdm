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

# Install yt-dlp
# RUN pip install --no-cache-dir yt-dlp

# Test pip install
# RUN pip freeze

# Install ffmpeg and ffprobe
# RUN apt-get update && apt-get install -y ffmpeg curl unzip imagemagick && rm -rf /var/lib/apt/lists/*
# RUN curl -L https://github.com/yt-dlp/yt-dlp/releases/latest/download/yt-dlp -o /app/yt-dlp # && chmod a+rx /app/yt-dlp && ls /app
# RUN curl -L https://github.com/ffbinaries/ffbinaries-prebuilt/releases/download/v4.4.1/ffmpeg-4.4.1-linux-64.zip -o /app/ffmpeg-4.4.1-linux-64.zip
# RUN unzip -o -j /app/ffmpeg-4.4.1-linux-64.zip -d /app
# RUN curl -L https://github.com/ffbinaries/ffbinaries-prebuilt/releases/download/v4.4.1/ffprobe-4.4.1-linux-64.zip -o /app/ffprobe-4.4.1-linux-64.zip
# RUN unzip -o -j /app/ffprobe-4.4.1-linux-64.zip -d /app
# RUN chmod a+rx /app/ffmpeg
# RUN chmod a+rx /app/ffprobe
# RUN rm -rf /app/ffmpeg-4.4.1-linux-64.zip /app/ffprobe-4.4.1-linux-64.zip

# Make port 5000 available to the world outside this container
EXPOSE 5000

# Run app.py when the container launches
CMD ["/bin/sh", "-c", "python app.py 2>&1"]
