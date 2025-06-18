import pandas as pd
from resubmission.utils import normalize_text, extract_drug_code, llm_response, processing_thoughts
from resubmission.prompt import prompt, duplicate_prompt, coverage_prompt, age_prompt, interaction_prompt
from resubmission.const import CODE, REASON, JUSTIFICATION, SERVICE, NORMALIZED, SFDA_CODE, SFDA_NAME
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent

drugs = pd.read_csv(BASE_DIR / "Data" / "SFDA.csv")
df = pd.read_csv(BASE_DIR / "Data" / "sample.csv")
lookup_prompt = {"Not clinically justified": prompt, "Therapeutic Duplication": duplicate_prompt, "Not Covered": coverage_prompt,
                 "Inconsistent with age": age_prompt, "Severe Interactions": interaction_prompt}

df[REASON] = df[REASON].astype(str)
df[NORMALIZED] = df[REASON].apply(normalize_text)
df = df.loc[~df[NORMALIZED].isnull()]
df[JUSTIFICATION] = None

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
        df.loc[i, JUSTIFICATION] = response

df.to_csv(BASE_DIR / "Data" / "results.csv", index=False)
