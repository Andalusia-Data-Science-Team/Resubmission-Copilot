FROM python:3.12-slim

WORKDIR /app

# Install prerequisites
RUN apt-get update && apt-get install -y \
    curl \
    gnupg \
    apt-transport-https

# Add Microsoft package repository
RUN curl https://packages.microsoft.com/keys/microsoft.asc | apt-key add - \
    && curl https://packages.microsoft.com/config/debian/11/prod.list > /etc/apt/sources.list.d/mssql-release.list

# Install ODBC driver and tools
RUN apt-get update \
    && ACCEPT_EULA=Y apt-get install -y \
        msodbcsql18 \
        unixodbc-dev \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY . .

EXPOSE 5000

CMD ["gunicorn", "-b", "0.0.0.0:5000", "flask_app:app"]