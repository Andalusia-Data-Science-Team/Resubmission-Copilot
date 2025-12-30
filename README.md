# Resubmission Copilot - Policy Assist

An intelligent AI-powered system for automating medical insurance claims resubmission processes. This application helps insurance teams quickly find policy details, understand coverage limits, and generate justifications for rejected claims.

![Python Version](https://img.shields.io/badge/python-3.10%2B-blue)
![Flask](https://img.shields.io/badge/flask-3.1.2-green)
![License](https://img.shields.io/badge/license-MIT-blue)

## 📋 Table of Contents

- [Overview](#-overview)
- [Features](#-features)
- [Architecture](#-architecture)
- [Prerequisites](#-prerequisites)
- [Installation](#-installation)
- [Configuration](#-configuration)
- [Usage](#-usage)
- [Project Structure](#-project-structure)
- [Development](#-development)
- [Troubleshooting](#-troubleshooting)
- [Contributing](#-contributing)
- [Authors](#-authors)

## 🎯 Overview

Resubmission Copilot streamlines the insurance claims resubmission workflow by:

1. **Smart Search**: Quickly locate Bupa visits with rejected claims (BE/CV rejection codes)
2. **Policy Analysis**: Automatically retrieve and display relevant insurance policy details
3. **AI Assistant**: Interactive chatbot powered by GPT that understands policy coverage, limits, and requirements
4. **Justification Generation**: One-click generation of detailed justifications for rejected services based on policy terms

## ✨ Features

### 🔍 Visit Management
- Search visits by visit ID, filtered with specific rejection codes (BE-*, CV-*)
- Display comprehensive visit details including services, diagnoses, and pricing

### 📊 Policy Intelligence
- Automatic policy matching based on policy number and class
- Detailed coverage breakdown by service type
- SFDA (Saudi Food & Drug Authority) medication validation

### 🤖 AI-Powered Assistance
- **Conversational Interface**: Ask questions about coverage limits, pre-approval requirements, and policy details
- **Context-Aware**: Understands the patient's specialty, diagnosis, and services provided
- **Justification Generator**: Creates evidence-based justifications citing specific policy clauses
- **Memory Management**: Maintains conversation history with smart context window management


## 🏗️ Architecture

```
┌─────────────────┐
│   Flask Web     │
│   Application   │
└────────┬────────┘
         │
    ┌────┴────┐
    │         │
┌───▼──┐  ┌──▼────┐
│ SQL  │  │MongoDB│
│Server│  │       │
└──────┘  └───┬───┘
              │
         ┌────▼─────┐
         │ LangGraph│
         │  Agent   │
         └────┬─────┘
              │
         ┌────▼─────┐
         │Fireworks │
         │   API    │
         └──────────┘
```

### Components

- **Flask Backend**: Handles routing, session management, and business logic
- **SQL Server**: Stores patient, visit, and billing data
- **MongoDB**: Stores structured insurance policy data
- **LangGraph Agent**: Manages conversational AI with memory and context
- **Fireworks LLM**: Powers the chatbot with GPT-OSS-120B model
- **LlamaExtract**: Extracts structured data from policy documents

## 📦 Prerequisites

### Software Requirements
- Python 3.10 or higher
- MongoDB 4.4+
- ODBC Driver 17 for SQL Server

## 🚀 Installation

### 1. Clone the Repository

```bash
git clone https://github.com/Andalusia-Data-Science-Team/Resubmission-Copilot.git
cd Resubmission-Copilot
```

### 2. Create Virtual Environment

```bash
python -m venv venv

# Windows
venv\Scripts\activate

# Linux/Mac
source venv/bin/activate
```

### 3. Install Dependencies

```bash
pip install -e .

```

## ⚙️ Configuration

### 1. Environment Variables

Create a `.env` file in the project root:

```env
# Flask Configuration
FLASK_SECRET_KEY=your-secret-key-here

# Fireworks AI API
FIREWORKS_API_KEY=your-fireworks-api-key

# LlamaCloud API
LLAMA_CLOUD_API_KEY=your-llamacloud-api-key
```

### 2. Database Configuration

Create `passcode.json` in the project root, structured like the following example:

```json
{
  "DB_NAMES": {
    "Replica": {
      "Server": "your-sql-server-host",
      "Database": "your-database-name",
      "UID": "your-username",
      "PWD": "your-password",
      "driver": "ODBC Driver 17 for SQL Server"
    }
  }
}
```

Create `database.ini` for MongoDB:

```ini
[mongodb]
db=insurance_db
host=mongo-server-machine-ip
port=27017
username=your-mongo-username
password=your-mongo-password
authentication_source=admin
```

### 3. SFDA Data

Ensure `Data/sfda_list.csv` exists with the following columns:
- `Service_Name`: Service/medication name
- `SFDAStatus`: Approval status
- `SFDACode`: SFDA registration code

## 🎮 Usage

### Starting the Application

```bash
# Development mode
python flask_app.py

# Production mode (with Gunicorn)
gunicorn -w 4 -b 0.0.0.0:2199 wsgi:app
```

The application will be available at `http://localhost:2199`

### Workflow

#### 1. Search for Visits
- Navigate to the home page
- Select a visit ID from the dropdown (pre-filtered for Bupa visits with rejections)
- Click "View Details"

#### 2. Review Policy & Visit Data
- View patient information, services provided, and rejection reasons
- Review matched insurance policy details and coverage limits
- Check SFDA medication status

#### 3. Use AI Assistant
Two ways to use the AI features:

**A. Chatbot** (Click "Ask Assistant" button):
- Ask questions about coverage: *"Is psychiatric examination covered?"*
- Check pre-authorization: *"Does this service require pre-approval?"*
- Verify limits: *"What's the annual limit for optical services?"*

**B. Generate Justifications**:
- Hover over any service row in the visit table
- Click "✨ Generate Justification"
- AI creates a detailed justification citing relevant policy clauses


## 📁 Project Structure

```
Resubmission-Copilot/
│
├── src/
│   └── resubmission/
│       ├── __init__.py
│       ├── chatbot.py              # LangGraph agent implementation
│       ├── models.py                # MongoDB schema definitions
│       ├── utils.py                 # Helper functions
│       ├── extraction.py            # Policy document extraction
│       ├── prompt.py                # LLM prompts
│       ├── config_handler.py        # Configuration loader
│       └── const.py                 # Constants
│
├── SQL/
│   ├── get_visits.sql              # Query for visit retrieval
│   └── resubmission.sql            # Main resubmission query
│
├── templates/
│   ├── layout.html                 # Base template
│   ├── index.html                  # Home/search page
│   ├── chat.html                   # Chat interface
│   └── error.html                  # Error page
│
├── static/
│   └── style.css                   # Custom styles
│
├── Data/
│   └── sfda_list.csv              # SFDA medication database
│
├── flask_app.py                    # Main Flask application
├── wsgi.py                         # WSGI entry point
├── pyproject.toml                  # Project metadata
├── setup.cfg                       # Setup configuration
├── database.ini                    # MongoDB config (create this)
├── passcode.json                   # SQL Server config (create this)
├── .env                            # Environment variables (create this)
└── README.md                       # This file
```


## 🛠️ Development

### Code Quality

```bash
# Sort imports
isort src/ tests/

# Format code
black src/ tests/

# Lint
flake8 src/ tests/

# Type checking
mypy src/

```

### Adding New Policies

#### File/Batch Extraction from PDF Example Usage
```python
from src.resubmission.extraction import ExtractAgent

# Loading an existing agent
agent = ExtractAgent('bupa')

# Batch Extraction
outputs = await agent.extract_batch("path/to/policy_data")
for output in outputs:
    insert(output.data)

# File Extraction
result = agent.extract_file("path/to/policy.pdf")
insert(result.data)
```

## 🐛 Troubleshooting

### Common Issues

#### 1. **"MongoDB connection timeout"**
```
Error: Cannot reach the MongoDB server
```
**Solution**: 
- Check MongoDB container is running
- Verify `database.ini` credentials are correct
- Test connection

```python
from mongoengine import connect
from src.resubmission.config_handler import config

params = config(section="mongodb")
connect(
    db=params["db"],
    host=params.get("host"),
    port=int(params.get("port")),
    username=params.get("username"),
    password=params.get("password"),
    authentication_source=params.get("authentication_source"),
)
```

#### 2. **"SQL Server connection failed"**
```
Errors: - Login timeout expired
        - Login failed for user <user>
```
**Solution**:
- Make sure `passcode.json` credentials being used are correct
- Kindly contact Data Engineering team / DBA if the issue persists

#### 3. **"SFDA data missing"**
```
KeyError: 'SFDAStatus'
```
**Solution**:
- Ensure `Data/sfda_list.csv` exists
- Verify CSV has required columns
- Check file encoding (UTF-8)

#### 4. **"Fireworks API error"**
```
Error: Invalid API key
```
**Solution**:
- Verify `FIREWORKS_API_KEY` in `.env`
- Check API quota/limits

### Debug Mode

Check application logs:
```bash
tail -f app.log
```

## 📚 Additional Resources

- [Flask Documentation](https://flask.palletsprojects.com/)
- [Llama Extract](https://developers.llamaindex.ai/python/cloud/llamaextract/getting_started/)
- [LangGraph Guide](https://langchain-ai.github.io/langgraph/)
- [MongoDB Documentation](https://docs.mongodb.com/)
- [Fireworks AI API](https://docs.fireworks.ai/)

## 🤝 Contributing

We welcome contributions! Please follow these steps:

1. Create a feature branch (`git checkout -b FEAT/amazing-feature`)
2. Make your changes
3. Format code using (`black .`) and sort the import using isort(`isort .`)
4. Commit changes (`git commit -m 'Add amazing feature'`)
5. Push to branch (`git push origin feature/amazing-feature`)
6. Open a Pull Request

### Coding Standards
- Follow PEP 8 style guide
- Add docstrings to all functions
- Write tests for new features
- Update README for significant changes

## 👥 Authors

**AI Team**
- [Nadine Muhammad](https://github.com/Nadine-Muhammad)
- [Rafik Sameh](https://github.com/RafikSameh)

---

**Built by Andalusia AI Team**

![check](https://github.com/Andalusia-Data-Science-Team/Resubmission-Copilot/actions/workflows/test.yml/badge.svg)
![check](https://github.com/Andalusia-Data-Science-Team/Resubmission-Copilot/actions/workflows/docs.yml/badge.svg)
