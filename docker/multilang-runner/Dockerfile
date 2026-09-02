FROM python:3.13-slim

# Install Node.js and a C++ compiler alongside Python (already in the base image)
RUN apt-get update && apt-get install -y --no-install-recommends \
    nodejs \
    npm \
    g++ \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /task