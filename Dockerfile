# Base Image
FROM python:3.12-slim

# Set the working directory in the container
WORKDIR /opt/stage0/processor

# Copy the Pipfile and Pipfile.lock to the container
COPY Pipfile Pipfile.lock ./

# Install pipenv
RUN pip install pipenv

# Install dependencies using pipenv
RUN pipenv install --deploy --system

# Copy the source code into the container
COPY src/ /opt/stage0/processor/

# Set Environment Variables
ENV PYTHONPATH=/opt/stage0/processor

# Command to run the application
CMD ["python", "-m", "main"]