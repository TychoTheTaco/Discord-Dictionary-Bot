FROM python:3.10

# Copy required files
WORKDIR /app
COPY ./discord_dictionary_bot ./discord_dictionary_bot
COPY ./requirements.txt .
COPY ./setup.py .

# Install ffmpeg
RUN apt-get update  \
    && apt-get install -y ffmpeg \
    && rm -rf /var/lib/apt/lists/*

# Install requirements
RUN pip install -r requirements.txt

# Install app
RUN pip install .

ENTRYPOINT ["python", "-m", "discord_dictionary_bot"]
