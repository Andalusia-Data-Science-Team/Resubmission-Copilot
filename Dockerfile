FROM python:3.12-slim

WORKDIR /app

# Install prerequisites
RUN apt-get update && apt-get install -y \
    gnupg \
    apt-transport-https \
    git \
    && rm -rf /var/lib/apt/lists/*

# Add Microsoft GPG key and repo list from local files
COPY microsoft.asc .
COPY mssql-release.list /etc/apt/sources.list.d/mssql-release.list

RUN gpg --dearmor -o /usr/share/keyrings/microsoft-prod.gpg < microsoft.asc \
    && rm microsoft.asc

# Install ODBC driver and tools
RUN apt-get update \
    && ACCEPT_EULA=Y apt-get install -y \
        msodbcsql17 \
        unixodbc-dev \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY . .

EXPOSE 2200

#RUN chmod +x run_flask_app.sh
#CMD ["./run_flask_app.sh"]
#CMD ["python3", "setup.py"]
#CMD ["gunicorn", "-w", "4", "-b", "0.0.0.0:2200", "wsgi:app"]
#CMD ["gunicorn", "-b", "0.0.0.0:2200", "flask_app:app"]