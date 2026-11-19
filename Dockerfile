# Dockerfile
# ----------
# A Dockerfile is a recipe that builds a "container image" — a self-contained
# box with Python and our app inside, so it runs the same on any machine.
# docker-compose uses this to build the gateway service.

# Start from a small official Python image.
FROM python:3.11-slim

# Don't write .pyc cache files, and show print/logs immediately (unbuffered).
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# All following commands run inside /app in the container.
WORKDIR /app

# Copy just the requirements first and install them. Doing this before copying
# the rest of the code lets Docker cache the installed packages, so rebuilds are
# fast when you change code but not dependencies.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Now copy the application code in.
COPY app ./app

# Start the web server. "0.0.0.0" means "listen on all network interfaces",
# which is required so the server is reachable from outside the container.
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
