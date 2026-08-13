# Use slim Python 3.12 image
FROM python:3.12-slim

# Set working directory
WORKDIR /app

# Install uv package manager
RUN pip install uv

# Copy dependency definition files
COPY pyproject.toml uv.lock ./

# Install dependencies using uv (without the project itself to maximize layer caching)
RUN uv sync --frozen --no-install-project --no-dev

# Copy the rest of the application source code
COPY . .

# Install the project code into the virtual environment
RUN uv sync --frozen --no-dev

# Ensure the virtual environment is on the PATH
ENV PATH="/app/.venv/bin:$PATH"

# Expose backend port
EXPOSE 4000

# Run the FastAPI application
CMD ["uvicorn", "singularity.api.app:app", "--host", "0.0.0.0", "--port", "4000"]
