import re
from dotenv import load_dotenv
from langchain_fireworks import ChatFireworks
from langchain_core.messages import HumanMessage, SystemMessage
from resubmission.const import MN11
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
        model=model, temperature=0.0, max_tokens=8000, model_kwargs={"top_k": 1}
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
