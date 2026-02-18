from datetime import date
import pandas as pd
from mongoengine import connect
from src.resubmission.config_handler import config
from src.resubmission.models import Policy
params = config(section="mongodb")

data = connect(
    db=params["db"],
    host=params.get("host"),
    port=int(params.get("port")),
    username=params.get("username"),
    password=params.get("password"),
    authentication_source=params.get("authentication_source"),
)
Total_policies = pd.DataFrame(columns=["policy_number", "effective_from", "effective_to"])
for policy in Policy.objects.only("policy_number", "effective_from", "effective_to"):
    print(policy.policy_number)
    Total_policies_policies = Total_policies._append({
        "policy_number": policy.policy_number,
        "effective_from": policy.effective_from,
        "effective_to": policy.effective_to
    }, ignore_index=True)
print(f"Total policies: {Policy.objects.count()}")

print("\t----- Active Policies -----")


today = date.today()
#print("policy_number\t|\teffective_from\t|\teffective_to")
available_policies = pd.DataFrame(columns=["policy_number", "effective_from", "effective_to"])
counter = 0
for policy in Policy.objects(
    effective_from__lte=today,
    effective_to__gte=today
).only("policy_number", "effective_from", "effective_to"):
    #print(f"{policy.policy_number}\t|\t{policy.effective_from}\t|\t{policy.effective_to}")
    available_policies = available_policies._append({
        "policy_number": policy.policy_number,
        "effective_from": policy.effective_from,
        "effective_to": policy.effective_to
    }, ignore_index=True)
    counter += 1

print(f"Total active policies: {counter}")
print(available_policies)

available_policies.to_excel("active_policies.xlsx", index=True)

print("\t----- Expired Policies -----")

expired_policies = pd.DataFrame(
    columns=["policy_number", "effective_from", "effective_to"]
)

counter = 0
for policy in Policy.objects(
    effective_to__lt=today
).only("policy_number", "effective_from", "effective_to"):

    expired_policies = expired_policies._append({
        "policy_number": policy.policy_number,
        "effective_from": policy.effective_from,
        "effective_to": policy.effective_to
    }, ignore_index=True)

    counter += 1

print(f"Total expired policies: {counter}")
print(expired_policies)

expired_policies.to_excel("expired_policies.xlsx", index=True)