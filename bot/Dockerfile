FROM python:slim

# Copy required files
WORKDIR /app
COPY ./discord_dictionary_bot ./discord_dictionary_bot
COPY ./requirements.txt .
COPY ./setup.py .

# Install ffmpeg
RUN apt-get update  \
    && apt-get install -y ffmpeg \
    && rm -rf /var/lib/apt/lists/*

# Install build dependencies and requirements
RUN apt-get update \
    && apt-get install -y --no-install-recommends gcc libc-dev \
    && rm -rf /var/lib/apt/lists/* \
    && pip install -r requirements.txt \
    && apt-get purge -y --auto-remove gcc libc-dev

# Install app
RUN pip install .

ENTRYPOINT ["python", "-m", "discord_dictionary_bot"]
