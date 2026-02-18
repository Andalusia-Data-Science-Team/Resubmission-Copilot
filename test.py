from dotenv import load_dotenv
from src.resubmission.prompt import bupa_prompt
from src.resubmission.models import Policy, NCCI_Policy
from src.resubmission.utils import _find_policy_by_number
import pandas as pd
load_dotenv()
# Initialize client (set LLAMA_CLOUD_API_KEY in your environment)


def _find_policy_by_number(policy_number_input):
    """
    Finds a policy by matching policy number (handles suffix variations).
    Args:
        policy_number_input: Policy number from input data
    Returns:
        Policy object or None
    """
    policy_numbers = list(
        NCCI_Policy.objects().only("policy_number").scalar("policy_number")
    )

    for policy_number in policy_numbers:
        # Check if input is substring of DB policy number (handles missing suffixes)
        if policy_number_input in policy_number:
            return NCCI_Policy.objects(policy_number=policy_number).first()

    return None
Policy_o = _find_policy_by_number("48594944")
print(pd.DataFrame([Policy_o.to_mongo().to_dict()]).to_excel("output.xlsx", index=False))