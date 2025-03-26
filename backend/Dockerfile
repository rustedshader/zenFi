FROM python:3.11-bookworm
ENV PYTHONUNBUFFERED True

RUN pip install --upgrade pip
COPY requirements.txt .
RUN pip install --no-cache-dir -r  requirements.txt

ENV APP_HOME /root
WORKDIR $APP_HOME
COPY /app $APP_HOME/app

EXPOSE 443
CMD ["fastapi", "run", "app/api/main.py", "--host", "0.0.0.0", "--port", "443"]