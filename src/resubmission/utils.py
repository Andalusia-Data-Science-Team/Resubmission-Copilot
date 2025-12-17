import json
import re
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime
from pathlib import Path

import pandas as pd
from dotenv import load_dotenv
from sqlalchemy import create_engine

from src.resubmission.models import CoverageDetail, Policy

sf = pd.read_csv(Path("Data") / "sfda_list.csv")

with open("passcode.json", "r") as file:
    db_configs = json.load(file)
db_configs = db_configs["DB_NAMES"]
read_passcode = db_configs["Replica"]

sql_path = Path("SQL")
with open(sql_path / "resubmission.sql", "r") as file:
    query = file.read()
with open(sql_path / "get_visits.sql", "r") as file:
    visits_query = file.read()

_ = load_dotenv()


def get_visits_by_date():
    df = read_data(visits_query, read_passcode, params=None)
    return df["VisitID"]


def get_policy_details(df, logger):
    """
    Retrieves policy and coverage details by matching policy number and VIP level.

    Args:
        df: DataFrame containing 'ContractorClientPolicyNumber' and 'Contract' columns

    Returns:
        tuple: (policy, detail_dict, available_levels)
            - policy: Policy object or None
            - detail_dict: Coverage detail dictionary or None
            - available_levels: List of available VIP levels (only when no match found) or None
    """
    policy_number_input = df["ContractorClientPolicyNumber"].iloc[0]
    vip_level_input = normalize_text(df["Contract"].iloc[0])

    # Find matching policy (handles suffix variations)
    policy = _find_policy_by_number(policy_number_input)
    if not policy:
        logger.info("No policy found")
        return None, None, None

    # Get coverage details for the matching VIP level
    detail, available_levels = _match_coverage_detail(policy, vip_level_input)

    return policy, detail, available_levels


def _find_policy_by_number(policy_number_input):
    """
    Finds a policy by matching policy number (handles suffix variations).
    Args:
        policy_number_input: Policy number from input data
    Returns:
        Policy object or None
    """
    policy_numbers = list(Policy.objects().only("policy_number").scalar("policy_number"))

    for policy_number in policy_numbers:
        # Check if input is substring of DB policy number (handles missing suffixes)
        if policy_number_input in policy_number:
            return Policy.objects(policy_number=policy_number).first()

    return None


def _match_coverage_detail(policy, vip_level_input):
    """
    Matches coverage detail by VIP level from policy.

    Args:
        policy: Policy object
        vip_level_input: Normalized VIP level from input

    Returns:
        tuple: (detail_dict, available_levels)
            - detail_dict: Matched coverage detail as sorted dict, or None
            - available_levels: List of available levels (only if no match), or None
    """
    coverage_details = policy.coverage_details

    # If only one coverage exists, return it directly
    if len(coverage_details) == 1:
        detail = coverage_details[0].to_mongo().to_dict()
        return dict(sorted(detail.items())), None

    # Try to match by VIP level
    matching_coverages = [
        c for c in coverage_details
        if normalize_text(c.vip_level) == vip_level_input
    ]

    if matching_coverages:
        detail = matching_coverages[0].to_mongo().to_dict()
        return dict(sorted(detail.items())), None

    # No match found - return available levels for error message
    available_levels = [c.vip_level for c in coverage_details]
    return None, available_levels


def get_visit_data(visit_id):
    """Fetch and process visit data by selected visit id"""
    df = read_data(query, read_passcode, (visit_id,))
    df["Contract"] = (
        df["Contract"]
        .fillna("")  # ensure no NaN
        .astype(str)
        .str.split("-", n=1)
        .pipe(lambda p: p.apply(lambda x: x[1].strip() if len(x) > 1 else x[0].strip()))
    )
    df = pd.merge(df, sf, on="Service_Name", how="left")

    # Format Start_Date consistently
    if "Start_Date" in df.columns and not df.empty:
        df["Start_Date"] = pd.to_datetime(df["Start_Date"]).dt.strftime(
            "%Y-%m-%d %H:%M:%S"
        )

    if df.empty:
        return None
    else:
        return df


def extract_drug_code(text):
    """
    Extract the drug codes in rejection reason strings.
    """
    pattern = r"\d+(?:\.\d+)?(?:-\d+(?:\.\d+)?){0,2}"
    codes = re.findall(pattern, text)
    return set(codes)


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
            datetime.fromisoformat(data.get("effective_to"))
            if data.get("effective_to") not in (None, "")
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
