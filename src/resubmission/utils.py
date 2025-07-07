import re
from bs4 import BeautifulSoup
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


def extract_discharge_summary(html):
    soup = BeautifulSoup(html, 'lxml')
    discharge_summary = []

    # Only extract from top-level, non-nested tags (e.g., h1, h2, h3, and .form-section blocks)
    for tag in soup.select('h1, h2, h3, div.form-section'):
        # Avoid re-processing nested divs
        if tag.name == 'div' and tag.find_parent('div', class_='form-section'):
            continue  # skip nested form-section divs

        text = tag.get_text(" ", strip=True)
        if text:
            discharge_summary.append(text)

    # Combine into a single string
    discharge_summary = "\n".join(discharge_summary)
    discharge_summary = re.sub(r'[\u0600-\u06FF]+', '', discharge_summary)

    return discharge_summary
