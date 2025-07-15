import pandas as pd
import json
import tqdm
from resubmission.utils import normalize_text, extract_drug_code, llm_response, processing_thoughts, read_data  # update_table
from resubmission.prompt import prompt, duplicate_prompt, coverage_prompt, age_prompt, interaction_prompt
from resubmission.const import CODE, REASON, JUSTIFICATION, SERVICE, NORMALIZED, SFDA_CODE, SFDA_NAME
from pathlib import Path
import logging
from logging.handlers import TimedRotatingFileHandler

BASE_DIR = Path(__file__).resolve().parent

LOG_DIR = BASE_DIR / "logs"
LOG_DIR.mkdir(exist_ok=True)
logger = logging.getLogger("performance_logs")
logger.setLevel(logging.DEBUG)
file_handler = TimedRotatingFileHandler(
    LOG_DIR / "performance.log", when="midnight", interval=1, backupCount=7, encoding="utf-8"
)
file_handler.setLevel(logging.DEBUG)
file_handler.setFormatter(logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s"))
if not logger.hasHandlers():
    logger.addHandler(file_handler)

drugs = pd.read_csv(BASE_DIR / "Data" / "SFDA.csv")
# edit with normalized reasons from nphies
lookup_prompt = {"Not clinically justified": prompt, "Therapeutic Duplication": duplicate_prompt, "Not Covered": coverage_prompt,
                 "Inconsistent with age": age_prompt, "Severe Interactions": interaction_prompt}

try:
    with open("passcode.json", "r") as file:
        db_configs = json.load(file)
    db_configs = db_configs["DB_NAMES"]
    read_passcode = db_configs["AHJ_DOT-CARE"]

    sql_path = Path("sql") / "resubmission.sql"
    with open(sql_path, "r") as file:
        query = file.read()

except Exception as e:
    logger.exception(f"Error loading configuration files: {e}")
    raise

df = read_data(query, read_passcode)

# select slice mn_df where reason == 'MN-11'
# mn_df = df.loc[df[REASON] == 'MN-11']
df[REASON] = df[REASON].astype(str)
df[NORMALIZED] = df[REASON].apply(normalize_text)
df = df.loc[~df[NORMALIZED].isnull()]
df[JUSTIFICATION] = None

logger.debug(f"Processing {len(df)} rows")  # mn_df
for i in tqdm(len(df), desc="Processing"):  # mn_df
    nor_res = df.loc[i, NORMALIZED]
    # Look for current service code in SFDA codes
    sfda_code = drugs[drugs[SFDA_CODE] == df.loc[i, CODE]]

    if nor_res == "No drug found for this code":
        if sfda_code.empty:
            df.loc[i, JUSTIFICATION] = "Drug code was not found in SFDA drug list, please consider revising this code"
        else:
            df.loc[i, JUSTIFICATION] = "Drug code exists in SFDA drug list under " + str(sfda_code.iloc[0].to_dict())

    else:
        info = str(df.loc[i, [SERVICE, "Diagnosis"]].to_dict())
        reason = str(df.loc[i, REASON])
        # To provide the LLM with the drug name if drug codes are mentioned in rejection reason
        meds = {}
        codes = extract_drug_code(reason)
        if codes:
            for code in codes:
                # Look for the drug code in SFDA codes and retrieve its name
                tmp = drugs[drugs[SFDA_CODE] == code]
                if not tmp.empty:
                    meds.update({code: tmp[SFDA_NAME].iloc[0]})

        response, thought = processing_thoughts(llm_response(info, reason, meds, lookup_prompt[nor_res]))
        df.loc[i, JUSTIFICATION] = response.replace("*", "")

df = df.drop([NORMALIZED], axis=1)
