# Resubmission Copilot

An intelligent AI-powered system for automating medical insurance claims resubmission processes. This application helps insurance teams quickly find policy details, understand coverage limits, and generate justifications for rejected claims.

![Python Version](https://img.shields.io/badge/python-3.10%2B-blue)
![Flask](https://img.shields.io/badge/flask-3.1.2-green)
![License](https://img.shields.io/badge/license-MIT-blue)

## 📋 Table of Contents

- [Overview](#overview)
- [Features](#features)
- [Architecture](#architecture)
- [Prerequisites](#prerequisites)
- [Installation](#installation)
- [Configuration](#configuration)
- [Usage](#usage)
- [Project Structure](#project-structure)
- [API Reference](#api-reference)
- [Database Schema](#database-schema)
- [Development](#development)
- [Troubleshooting](#troubleshooting)
- [Contributing](#contributing)
- [License](#license)

## 🎯 Overview

Resubmission Copilot streamlines the insurance claims resubmission workflow by:

1. **Smart Search**: Quickly locate Bupa visits with rejected claims (BE/CV rejection codes)
2. **Policy Analysis**: Automatically retrieve and display relevant insurance policy details
3. **AI Assistant**: Interactive chatbot powered by GPT that understands policy coverage, limits, and requirements
4. **Justification Generation**: One-click generation of detailed justifications for rejected services based on policy terms

## ✨ Features

### 🔍 Visit Management
- Search visits by date range or visit ID
- Filter for visits with specific rejection codes (BE-*, CV-*)
- Display comprehensive visit details including services, diagnoses, and pricing

### 📊 Policy Intelligence
- Automatic policy matching based on policy number and VIP level
- Detailed coverage breakdown by service type
- SFDA (Saudi Food & Drug Authority) medication validation
- Pre-authorization requirement detection

### 🤖 AI-Powered Assistance
- **Conversational Interface**: Ask questions about coverage limits, pre-approval requirements, and policy details
- **Context-Aware**: Understands the patient's specialty, diagnosis, and services provided
- **Justification Generator**: Creates evidence-based justifications citing specific policy clauses
- **Memory Management**: Maintains conversation history with smart context window management

### 💡 User Experience
- Clean, modern UI with responsive design
- Real-time chat interface with typing indicators
- One-click justification generation from service table
- Color-coded status indicators and badges

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
         │   LLM    │
         └──────────┘
```

### Components

- **Flask Backend**: Handles routing, session management, and business logic
- **SQL Server**: Stores visit data, claims, and financial information
- **MongoDB**: Stores structured insurance policy documents
- **LangGraph Agent**: Manages conversational AI with memory and context
- **Fireworks LLM**: Powers the chatbot with GPT-OSS-120B model
- **LlamaExtract**: Extracts structured data from policy documents

## 📦 Prerequisites

### Software Requirements
- Python 3.10 or higher
- SQL Server (with ODBC driver)
- MongoDB 4.4+
- ODBC Driver 17 for SQL Server

### System Requirements
- 4GB RAM minimum (8GB recommended)
- 2GB free disk space
- Network access to database servers

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

# For development
pip install -e ".[testing]"
```

### 4. Install ODBC Driver

**Windows**: Download and install [Microsoft ODBC Driver 17](https://docs.microsoft.com/en-us/sql/connect/odbc/download-odbc-driver-for-sql-server)

**Linux (Ubuntu/Debian)**:
```bash
curl https://packages.microsoft.com/keys/microsoft.asc | apt-key add -
curl https://packages.microsoft.com/config/ubuntu/20.04/prod.list > /etc/apt/sources.list.d/mssql-release.list
apt-get update
ACCEPT_EULA=Y apt-get install -y msodbcsql17
```

**macOS**:
```bash
brew tap microsoft/mssql-release https://github.com/Microsoft/homebrew-mssql-release
brew update
HOMEBREW_NO_ENV_FILTERING=1 ACCEPT_EULA=Y brew install msodbcsql17
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

Create `passcode.json` in the project root:

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
db=insurance_policies
host=localhost
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
- Check SFDA medication approval status

#### 3. Use AI Assistant
Two ways to access the AI assistant:

**A. Chat Interface** (Click "Ask Assistant" button):
- Ask questions about coverage: *"Is psychiatric examination covered?"*
- Check pre-authorization: *"Does this service require pre-approval?"*
- Verify limits: *"What's the annual limit for optical services?"*

**B. Generate Justifications**:
- Hover over any service row in the visit table
- Click "✨ Generate Justification"
- AI creates a detailed justification citing relevant policy clauses

#### 4. Copy & Submit
- Copy generated justifications
- Use them in your resubmission documentation
- Submit to insurance company

### Example Queries

```
User: "Is kidney transplant covered under this policy?"
Assistant: "Yes, kidney transplant is covered with a limit of 250,000 SR 
according to the policy's coverage details for VIP level."

User: "Does the psychiatric examination require pre-authorization?"
Assistant: "No, according to the policy's Approval Preauthorization Notes, 
no pre-authorization is required for outpatient services except those with 
specific limits (dental, optical, maternity, etc.). Psychiatric services 
are not among the exceptions."
```

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

## 🔌 API Reference

### Routes

#### `GET/POST /`
**Home page** - Visit search and selection

**POST Parameters**:
- `visit_id` (string): Selected visit ID

**Returns**: Renders `index.html`

---

#### `GET/POST /visit/<visit_id>`
**Policy details page** - Display visit data and matched policy

**Returns**: Renders `index.html` with policy and visit data, or `error.html` if not found

---

#### `GET/POST /chat/<visit_id>`
**Chat interface** - AI assistant interaction

**POST (Form)**: Send chat message
- `message` (string): User's question
- **Returns**: JSON `{"response": "assistant's reply"}`

**POST (JSON)**: Generate justification
- Body: Service details object
- **Returns**: JSON `{"justification": "generated text"}`

---

### Agent Functions

```python
def get_agent_response(
    user_input: str,
    thread_id: str,
    policy: str = "",
    visit_info: str = "",
    service: dict = None
) -> str
```

**Parameters**:
- `user_input`: User's question (None for justification mode)
- `thread_id`: Unique conversation identifier
- `policy`: JSON string of policy details
- `visit_info`: String containing visit context
- `service`: Dictionary of service details for justification

**Returns**: AI-generated response text

## 🗄️ Database Schema

### SQL Server Tables

**VisitMgt.VisitFinincailInfo**
```sql
VisitID                         INT
ContractorEnName                NVARCHAR(255)
ContractorClientPolicyNumber    NVARCHAR(50)
ContractorClientEnName          NVARCHAR(255)
ContractEnName                  NVARCHAR(255)
CreatedDate                     DATETIME
```

**Nphies.ClaimTransaction**
```sql
ID                  INT
VisitId             INT
StatementID         INT
TransactionType     NVARCHAR(50)
CreatedDate         DATETIME
```

**Nphies.ClaimItem**
```sql
ClaimTransactionID      INT
NameEn                  NVARCHAR(255)
ResponseReasonCode      NVARCHAR(50)
ResponseReason          NVARCHAR(MAX)
ResponseSubmitted       DECIMAL(18,2)
ITEMID                  INT
```

### MongoDB Schema

**Collection: Policy**
```javascript
{
  policy_number: String (required),
  company_name: String,
  policy_holder: String,
  effective_from: Date,
  effective_to: Date,
  coverage_details: [
    {
      vip_level: String,
      overall_annual_limit: String,
      inpatient_outpatient_treatment: String,
      accommodation: String,
      outpatient_deductible_mpn: String,
      outpatient_deductible_hospitals: String,
      outpatient_deductible_polyclinic: String,
      branded_medication_deductible: String,
      generic_medication_deductible: String,
      network: String,
      // ... 40+ coverage fields
      special_instructions: String
    }
  ]
}
```

See `schema.json` for complete field definitions.

## 🛠️ Development

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=src/resubmission

# Watch mode (auto-rerun on changes)
pytest-watcher
```

### Code Quality

```bash
# Format code
black src/ tests/

# Lint
flake8 src/ tests/

# Type checking
mypy src/
```

### Adding New Policies

#### Option 1: Manual Entry
```python
from src.resubmission.utils import insert

policy_data = {
    "policy_number": "12345",
    "company_name": "Example Corp",
    "policy_holder": "John Doe",
    "effective_from": "2025-01-01",
    "effective_to": "2026-01-01",
    "coverage_details": [
        {
            "vip_level": "VIP",
            "overall_annual_limit": "1,000,000 SR",
            # ... other fields
        }
    ]
}

insert(policy_data)
```

#### Option 2: Extract from PDF
```python
from src.resubmission.extraction import ExtractAgent

agent = ExtractAgent(
    name="bupa_extractor",
    schema="schema.json",
    prompt="Your extraction prompt"
)

result = agent.extract_file("path/to/policy.pdf")
insert(result.data)
```

### Environment Setup

```bash
# Development dependencies
pip install -e ".[testing]"

# Pre-commit hooks (recommended)
pip install pre-commit
pre-commit install
```

## 🐛 Troubleshooting

### Common Issues

#### 1. **"MongoDB connection timeout"**
```
Error: Cannot reach the MongoDB server
```
**Solution**: 
- Check MongoDB is running: `sudo systemctl status mongod`
- Verify `database.ini` credentials
- Check firewall: `sudo ufw allow 27017`
- Test connection: `mongo --host localhost --port 27017`

#### 2. **"SQL Server connection failed"**
```
Error: [Microsoft][ODBC Driver 17 for SQL Server]Login timeout expired
```
**Solution**:
- Verify SQL Server is accessible
- Check `passcode.json` credentials
- Test ODBC driver: `odbcinst -j`
- Verify network connectivity

#### 3. **"No Bupa visits found"**
**Solution**:
- Check date range in database
- Verify `ContractorEnName = 'Bupa'` in SQL
- Check rejection codes (BE-*, CV-*)

#### 4. **"SFDA data missing"**
```
KeyError: 'SFDAStatus'
```
**Solution**:
- Ensure `Data/sfda_list.csv` exists
- Verify CSV has required columns
- Check file encoding (UTF-8)

#### 5. **"Policy not found for VIP level"**
**Solution**:
- Check available levels in error message
- Verify policy number format (may include suffixes)
- Use `normalize_text()` for comparison
- Check MongoDB has policy data

#### 6. **"Fireworks API error"**
```
Error: Invalid API key
```
**Solution**:
- Verify `FIREWORKS_API_KEY` in `.env`
- Check API quota/limits
- Test with: `curl -H "Authorization: Bearer $FIREWORKS_API_KEY"`

### Debug Mode

Enable detailed logging:

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

Check application logs:
```bash
tail -f app.log
```

## 📚 Additional Resources

- [Flask Documentation](https://flask.palletsprojects.com/)
- [LangGraph Guide](https://langchain-ai.github.io/langgraph/)
- [MongoDB Documentation](https://docs.mongodb.com/)
- [Fireworks AI API](https://docs.fireworks.ai/)

## 🤝 Contributing

We welcome contributions! Please follow these steps:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Make your changes
4. Run tests (`pytest`)
5. Format code (`black .`)
6. Commit changes (`git commit -m 'Add amazing feature'`)
7. Push to branch (`git push origin feature/amazing-feature`)
8. Open a Pull Request

### Coding Standards
- Follow PEP 8 style guide
- Add docstrings to all functions
- Write tests for new features
- Update README for significant changes

## 📄 License

This project is licensed under the MIT License. See `LICENSE` file for details.

## 👥 Authors

**AI Team**
- Email: nadeensokily@gmail.com

## 🙏 Acknowledgments

- Anthropic Claude for documentation assistance
- Fireworks AI for LLM infrastructure
- LlamaIndex for document extraction capabilities
- The Flask and LangChain communities

## 📞 Support

For issues and questions:
- Open an issue on GitHub
- Email: nadeensokily@gmail.com
- Check existing documentation and troubleshooting section

---

**Built with ❤️ by the Andalusia Data Science Team**
![check](https://github.com/Andalusia-Data-Science-Team/Resubmission-Copilot/actions/workflows/test.yml/badge.svg)
![check](https://github.com/Andalusia-Data-Science-Team/Resubmission-Copilot/actions/workflows/docs.yml/badge.svg)