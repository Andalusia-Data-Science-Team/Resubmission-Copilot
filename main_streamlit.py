import pandas as pd
import streamlit as st
from resubmission.utils import normalize_text, extract_drug_code, llm_response, processing_thoughts
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

# Rotating file handler: rotates daily, keeps 7 backups
file_handler = TimedRotatingFileHandler(
    LOG_DIR / "performance.log", when="midnight", interval=1, backupCount=7, encoding="utf-8"
)
file_handler.setLevel(logging.DEBUG)
file_handler.setFormatter(logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s"))

if not logger.hasHandlers():
    logger.addHandler(file_handler)

drugs = pd.read_csv(BASE_DIR / "Data" / "SFDA.csv")
lookup_prompt = {"Not clinically justified": prompt, "Therapeutic Duplication": duplicate_prompt, "Not Covered": coverage_prompt,
                 "Inconsistent with age": age_prompt, "Severe Interactions": interaction_prompt}

st.title("Resubmission Copilot")
st.markdown("### Upload Rejections Data")
uploaded_file = st.file_uploader(
    "Upload a CSV or Excel file",
    type=["csv", "xls", "xlsx"],
)
if uploaded_file:
    file_extension = uploaded_file.name.split(".")[-1]
    if file_extension == "csv":
        df = pd.read_csv(uploaded_file)
    elif file_extension in ["xls", "xlsx"]:
        df = pd.read_excel(uploaded_file)

    df[REASON] = df[REASON].astype(str)
    df[NORMALIZED] = df[REASON].apply(normalize_text)
    df = df.loc[~df[NORMALIZED].isnull()]
    df[JUSTIFICATION] = None

    if st.button("Generate Responses"):
        logger.debug(f"Processing {len(df)} rows")
        progress_bar = st.progress(0, text="0% Complete")
        for i in range(len(df)):
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
            prgrs = round((i + 1)/len(df)*100)
            progress_bar.progress(prgrs, text=f"{prgrs}% Complete")

        df = df.drop([NORMALIZED], axis=1)
        edited_df = st.data_editor(df, num_rows="dynamic", use_container_width=True)
        st.markdown("### 📥 Download Generated Justifications")
        csv = edited_df.to_csv(index=False).encode("utf-8")
        st.download_button(
            label="Download as CSV",
            data=csv,
            file_name="results.csv",
            mime="text/csv",
        )
