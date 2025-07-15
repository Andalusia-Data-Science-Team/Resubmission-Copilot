import re
import pandas as pd
from dotenv import load_dotenv
from langchain_fireworks import ChatFireworks
from langchain_core.messages import HumanMessage, SystemMessage
from resubmission.const import MN11
import urllib.request
import urllib.parse
import urllib.error
from sqlalchemy import create_engine
import time
from main import logger
from Typing import Dict
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
    r"not covered": "Not Covered"
}


def normalize_text(text):
    for pattern, category in normalized.items():
        if re.search(pattern, text.lower()):
            return category


def extract_drug_code(text):
    """
    Extract the drug codes in rejection reason strings.
    """
    pattern = r'\d+(?:\.\d+)?(?:-\d+(?:\.\d+)?){0,2}'
    codes = re.findall(pattern, text)
    return set(codes)


def llm_response(info, reason, meds, prompt, model="accounts/fireworks/models/qwen3-235b-a22b"):
    chat_model = ChatFireworks(
        model=model, temperature=0.2, max_tokens=11000, model_kwargs={"top_k": 1}
    )

    chat_history = [
        SystemMessage(content=prompt),
        HumanMessage(content=info),
        HumanMessage(content="Rejection Reason Provided by Insurance Company: " + reason),
    ]
    if meds:
        chat_history.append(HumanMessage(content=str(meds)))

    response = chat_model.invoke(chat_history).content
    return response


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
        logger.debug(f"Database connection engine created for {server}/{db}")
        return engine
    except KeyError as e:
        logger.error(f"Missing key in passcodes dictionary: {e}")
        raise
    except Exception as e:
        logger.exception(f"Error creating database connection engine: {e}")
        raise


def read_data(query, read_passcode):
    """
    Executes a SQL query using get_conn_engine. If the first attempt fails,
    waits for 5 minutes before trying again. If second attempt fails, reads data from live instead.

    Returns:
        pandas DataFrame with query results
    """
    try:
        df = pd.read_sql_query(query, get_conn_engine(read_passcode))
        return df
    except Exception as e:
        logger.debug(f"First attempt failed with error: {str(e)}")
        logger.debug("Waiting 5 minutes before retrying...")
        time.sleep(300)  # Wait for 5 minutes (300 seconds)
        df = pd.read_sql_query(query, get_conn_engine(read_passcode))
        return df


def update_table(passcode: Dict[str, str], table_name: str, df: pd.DataFrame, retries=28, delay=500):
    """
    Updates a database table with the given DataFrame. Retries on failure.

    Parameters:
    - table_name: Name of the table to update.
    - df: DataFrame to update the table.
    - retries: Number of retry attempts.
    - delay: Delay in seconds between retries.
    """
    try:
        engine = get_conn_engine(passcode)
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
