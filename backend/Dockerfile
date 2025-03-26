FROM python:3.11-bookworm
ENV PYTHONUNBUFFERED True

# Upgrade pip and install dependencies
RUN pip install --upgrade pip
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Set the app home directory and copy files
ENV APP_HOME /home/rustedshader/gdg_hunterz/backend
WORKDIR $APP_HOME
COPY app $APP_HOME/app

# Expose port 8000 (non-privileged)
EXPOSE 8000

# Run Uvicorn on port 8000
CMD ["uvicorn", "app.api.main:app", "--host", "0.0.0.0", "--port", "8000"]