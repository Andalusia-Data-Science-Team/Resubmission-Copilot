import re
import pandas as pd
from dotenv import load_dotenv
from langchain_fireworks import ChatFireworks
from langchain_core.messages import HumanMessage, SystemMessage
from src.resubmission.const import MN11
from src.resubmission.models import Policy, CoverageDetail
from src.resubmission.prompt import chatbot_prompt
import urllib.request
import urllib.parse
import urllib.error
from sqlalchemy import create_engine
import time
from typing import Dict
from pathlib import Path
import json
from datetime import datetime


_ = load_dotenv()

normalized = {
    r"not.*indicated": MN11,
    r"not.*justified": MN11,
    r"no.*necessity": MN11,
    r"inconsistent.*diagnosis|diagnosis.*inconsistent": MN11,
    r"not related.*diagnosis|diagnosis.*not related": MN11,
    r"therapeutic duplication": "Therapeutic Duplication",
    r"\bage\b": "Inconsistent with age",
    r"interactions": "Severe Interactions",
    r"contradiction\s*": "Severe Interactions",
    r"not found.*code": "No drug found for this code",
    r"wrong.*code": "No drug found for this code",
    r"not covered": "Not Covered",
}


def extract_drug_code(text):
    """
    Extract the drug codes in rejection reason strings.
    """
    pattern = r"\d+(?:\.\d+)?(?:-\d+(?:\.\d+)?){0,2}"
    codes = re.findall(pattern, text)
    return set(codes)


def llm_response(
    policy, visit_info, question, model="accounts/fireworks/models/gpt-oss-120b"
):
    chat_model = ChatFireworks(model=model, temperature=0.2, max_tokens=5000)
    chat_history = [
        SystemMessage(content=chatbot_prompt),
        HumanMessage(content=policy),
        SystemMessage(
            content="""For your context, these are the services that were provided to the patient during their visit to the hospital.
        You should reference to them if you're asked about it directly.
        """
        ),
        HumanMessage(content=visit_info),
        HumanMessage(content=question),
    ]
    response = chat_model.invoke(chat_history).content
    return response


def data_prep(df):
    patient_info = str(
        df[
            [
                "Gender",
                "Age",
                "Diagnosis",
                "ICD10",
                "ProblemNote",
                "Chief_Complaint",
                "Symptoms",
            ]
        ]
        .iloc[0]
        .dropna()
        .to_dict()
    )
    services = str(
        df[["Service_id", "Service_Name", "Note", "Reason"]]
        .dropna(axis=1)
        .set_index("Service_id")
        .to_dict(orient="records")
    )
    return patient_info, services


def processing_thoughts(text):
    pattern = r"<think>(.*?)</think>"
    text_in_between = re.findall(pattern, str(text), re.DOTALL)
    clean_text = re.sub(pattern, "", text, flags=re.DOTALL)
    return clean_text.strip(), text_in_between[0].strip()


def get_conn_engine(passcodes):
    """
    Creates and returns a SQLAlchemy engine for connecting to the SQL database.

    Args:
    - passcodes (dict): A dictionary containing database credentials.

    Returns:
    - engine (sqlalchemy.engine.Engine): A SQLAlchemy Engine instance for connecting to the database.
    """
    try:
        server, db, uid, pwd, driver = (
            passcodes["Server"],
            passcodes["Database"],
            passcodes["UID"],
            passcodes["PWD"],
            passcodes["driver"],
        )
        params = urllib.parse.quote_plus(
            f"DRIVER={driver};"
            f"SERVER={server};"
            f"DATABASE={db};"
            f"UID={uid};"
            f"PWD={pwd};"
            f"Connection Timeout=300;"
        )
        engine = create_engine("mssql+pyodbc:///?odbc_connect={}".format(params))
        return engine
    except KeyError as e:
        print(f"Missing key in passcodes dictionary: {e}")
        raise
    except Exception as e:
        print(f"Error creating database connection engine: {e}")
        raise


def read_data(query, passcode, params):
    """
    Executes a SQL query using get_conn_engine. If the first attempt fails,
    waits for 5 minutes before trying again. If second attempt fails, reads data from live instead.

    Returns:
        pandas DataFrame with query results
    """
    try:
        df = pd.read_sql_query(query, get_conn_engine(passcode), params=params)
        return df
    except Exception as e:
        print(e)
        time.sleep(300)  # Wait for 5 minutes (300 seconds)
        df = pd.read_sql_query(query, get_conn_engine(passcode), params=params)
        return df


def update_table(
    passcode: Dict[str, str],
    table_name: str,
    df: pd.DataFrame,
    logger,
    retries=28,
    delay=500,
):
    """
    Updates a database table with the given DataFrame. Retries on failure.

    Parameters:
    - table_name: Name of the table to update.
    - df: DataFrame to update the table.
    - retries: Number of retry attempts.
    - delay: Delay in seconds between retries.
    """
    try:
        engine = get_conn_engine(passcode, logger)
        # Create a copy of the DataFrame to avoid modifying the original
        df_clean = df.copy()

        attempt = 0
        while attempt < retries:
            try:
                logger.debug(f"Update attempt {attempt+1}/{retries}")
                logger.debug("Connection established, beginning data transfer")
                df_clean.to_sql(
                    name=f"{table_name}",
                    con=engine,
                    index=False,
                    if_exists="append",
                    chunksize=1000,
                    schema="dbo",
                )
                logger.info(f"Successfully updated '{table_name}' table")
                return  # Exit the function if successful
            except Exception as e:
                attempt += 1
                logger.error(f"Attempt {attempt} failed: {str(e)}")
                if attempt < retries:
                    logger.info(f"Retrying in {delay} seconds...")
                    time.sleep(delay)
                else:
                    failure_msg = "All retries failed. Please check the error and try again later."
                    logger.error(failure_msg)
                    raise  # Re-raise the exception after all retries fail
    except Exception as e:
        logger.exception(f"Critical error in updating table {table_name}: {e}")
        raise


def list_files(folder_path: str):
    """
    Return a list of file names in the given folder.
    """
    p = Path(folder_path)
    if not p.is_dir():
        raise ValueError(f"{folder_path} is not a valid directory")

    return [str(f) for f in p.iterdir() if f.is_file()]


def insert(data_source):
    """
    Insert a Policy document from either a JSON file path or a Python dict.
    Validates and doesn't insert if a policy with the same policy_number already exists.
    """
    # --- Load data ---
    if isinstance(data_source, str):
        with open(data_source, "r") as f:
            data = json.load(f)
    elif isinstance(data_source, dict):
        data = data_source
    else:
        raise TypeError("data_source must be a dict or JSON file path")

    policy_number = data.get("policy_number")
    if not policy_number:
        raise ValueError("Missing required field: 'policy_number'")

    # --- Check for existing policy ---
    existing = Policy.objects(policy_number=policy_number).first()
    if existing:
        print(f"Policy {policy_number} already exists. Skipping insert.")
        return existing  # return the existing one instead of re-inserting

    # --- Parse coverage details ---
    coverage_list = [
        CoverageDetail(**coverage) for coverage in data.get("coverage_details", [])
    ]

    # --- Create Policy object ---
    policy = Policy(
        policy_number=policy_number,
        company_name=data.get("company_name"),
        policy_holder=data.get("policy_holder"),
        effective_from=(
            datetime.fromisoformat(data["effective_from"])
            if "effective_from" in data
            else None
        ),
        effective_to=(
            datetime.fromisoformat(data["effective_to"])
            if "effective_to" in data
            else None
        ),
        coverage_details=coverage_list,
    )

    policy.save()
    print(f"Policy {policy.policy_number} inserted successfully.")


def delete(policy_number: str):
    """
    Delete a Policy document from MongoDB by its policy_number.

    Args:
        policy_number (str): The policy number of the document to delete.

    Returns:
        bool: True if a document was deleted, False otherwise.
    """
    policy = Policy.objects(policy_number=policy_number).first()

    if not policy:
        print(f"Policy {policy_number} not found.")
        return False

    policy.delete()
    print(f"Policy {policy_number} deleted successfully.")
    return True


def normalize_text(text: str) -> str:
    if not isinstance(text, str):
        return text  # handle non-string values safely
    return text.replace(" ", "").replace("–", "").replace("-", "").lower()
