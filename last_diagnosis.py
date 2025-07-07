import pandas as pd
from langchain_fireworks import ChatFireworks
from langchain_core.messages import HumanMessage, SystemMessage
from rapidfuzz import fuzz
from pathlib import Path
import json
from resubmission.utils import processing_thoughts
import streamlit as st

st.title("Final Diagnosis")

BASE_DIR = Path(__file__).resolve().parent
icd = pd.read_csv(BASE_DIR / "Data" / "idc10_disease_full_data.csv")
df = pd.read_csv(BASE_DIR / "Data" / "final_diagnosis_1jul.csv")
cols = ["specialty", "Height", "Weight", "BMIValue", "BMI_StatusEN", "Vital_Sign1", "Vital_SignType", "DiagnoseName", "ICDDiagnoseCode", "Age",
        "Gender_Description", "ChiefComplaintNotes", "SymptomNotes"]
schema = {
    "type": "object",
    "properties": {
        "Primary Diagnosis": {
            "type": "object",
            "properties": {
                "Diagnosis": {
                    "type": "string",
                    "description": "Primary diagnosis description"
                },
                "ICD10": {
                    "type": "string",
                    "description": "ICD10 code for the primary diagnosis"
                }
            },
            "required": ["Diagnosis", "ICD10"],
            "additionalProperties": False
        },
        "Secondary Diagnoses": {
            "type": "object",
            "properties": {
                "Diagnosis": {
                    "type": "array",
                    "items": {
                        "type": "string",
                        "description": "Secondary diagnosis description"
                    }
                },
                "ICD10": {
                    "type": "array",
                    "items": {
                        "type": "string",
                        "description": "ICD10 code for secondary diagnosis"
                    }
                }
            },
            "required": ["Diagnosis", "ICD10"],
            "additionalProperties": False
        }
    },
    "required": ["Primary Diagnosis"],
    "additionalProperties": False
}
# st.write("Data Preview: ", df.head(10))
#df = df.loc[(df["medicaldepartment"] == "Outpatient") & ~(df["Note"].isnull())]
selected_pid = st.selectbox("Select Patient ID: ", df["patient_id"].unique())
sub = df.loc[df["patient_id"] == selected_pid]
st.dataframe(sub)


def summarize_notes(df):
    unique_notes: list[str] = []

    for idx, note in enumerate(df["Note"]):
        is_similar = False
        for existing in unique_notes:
            score = fuzz.token_sort_ratio(note, existing)
            if score > 50:
                is_similar = True
                break
        if not is_similar:
            unique_notes.append(note)

    return unique_notes


def call_llm(df, notes, model="accounts/fireworks/models/qwen3-235b-a22b"):
    json_model = ChatFireworks(model=model, temperature=0.0, max_tokens=11000, model_kwargs={"top_k": 1}).bind(
        response_format={"type": "json_object", "schema": schema}
    )
    chat_history = [
        SystemMessage(content="You are a helpful medical expert. You will be provided with a patient's information during their stay at the hospital, the initial diagnosis and ICD10 code"),
        HumanMessage(content=str(df[cols].iloc[0].to_dict())),
        HumanMessage(content="Patient's progress and medication notes: " + str(notes)),
        SystemMessage(content="""Based on this information, in your medical opinion, what is the final diagnosis and ICD10 for this patient?
         Provide secondary diagnoses too if exists/if necessary, and sort them by order of most relevant or important.
         Return the output in a valid JSON schema like the following format:
         {"Primary Diagnosis": {"Diagnosis": "Intracerebral hemorrhage, nontraumatic", "ICD10": "I61.9"},
          "Secondary Diagnoses": {"Diagnosis": ["Septic shock due to Klebsiella pneumoniae","Acute kidney injury"], "ICD10": ["A41.52","N17.9"]}}
         You must be 100% sure of the provided ICD10 codes. They must align with the disease descriptions.
         """),
    ]
    return json_model.invoke(chat_history).content


def get_description(raw_response):
    primary = json.loads(raw_response).get("Primary Diagnosis", {})
    secondary = json.loads(raw_response).get("Secondary Diagnoses", {})
    # try:
    #     code_mapping = icd.loc[icd["diseaseCode"] == primary['ICD10'], 'diseaseDescription'].iloc[0]
    # except Exception:
    #     code_mapping = None
    # if code_mapping:
    #     primary['Diagnosis'] = code_mapping

    # i = 0
    # for code in secondary['ICD10']:
    #     try:
    #         code_mapping = icd.loc[icd["diseaseCode"] == code, 'diseaseDescription'].iloc[0]
    #     except Exception:
    #         code_mapping = None
    #         pass
    #     if code_mapping:
    #         secondary['Diagnosis'][i] = code_mapping
    #     i += 1
    return primary, secondary


df["Note"] = df["Note"].str.lower()
df = df.drop_duplicates()

if st.button("Get Predictions"):
    notes = summarize_notes(sub)
    answer = call_llm(sub, notes)
    response, thought = processing_thoughts(answer)
    response = response.replace("\n", "")
    primary, secondary = get_description(response)

    # st.header("Summary of Progress Notes: ")
    # st.markdown(str(notes))

    st.header("Primary Diagnosis: ")
    st.markdown(str(primary["Diagnosis"]))
    st.markdown(str(primary["ICD10"]))

    st.header("Secondary Diagnoses: ")
    secondary = pd.DataFrame(secondary)
    st.dataframe(secondary)

    st.header("Model Reasoning: ")
    st.markdown(thought)
