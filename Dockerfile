# Use a lightweight, official Python image
FROM python:3.11-slim

# Set the working directory inside the container
WORKDIR /app

# Copy the source code into the container
COPY src/main.py .

# Install Python dependencies
RUN pip install --no-cache-dir Flask requests Flask-Cors

# Tell Docker that the container listens on this port
EXPOSE 9876

# The command to run when the container starts
CMD ["python", "main.py"]