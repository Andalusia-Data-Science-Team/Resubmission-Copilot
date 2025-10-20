from flask import Flask, render_template, request, redirect, url_for, jsonify, session
import pandas as pd
from resubmission.models import Policy
from resubmission.utils import llm_response, normalize_text, read_data
import json
from pathlib import Path

app = Flask(__name__)
app.secret_key = "your-secret-key-here"  # Change this to a random secret key

with open("passcode.json", "r") as file:
    db_configs = json.load(file)
db_configs = db_configs["DB_NAMES"]
read_passcode = db_configs["Replica"]

sql_path = Path("SQL") / "resubmission.sql"
with open(sql_path, "r") as file:
    query = file.read()

sf = pd.read_csv("Data/sfda_list.csv").rename(columns={"NameEn": "Service_Name"})


def get_visit_data(visit_id):
    """Fetch and process visit data once"""
    df = read_data(query, read_passcode, params=(visit_id,))
    df["Contract"] = (
        df["Contract"]
        .astype(str)
        .str.split("-", n=1)
        .pipe(lambda p: p.str[1].str.strip().fillna(p.str[0].str.strip()))
    )
    df = pd.merge(df, sf, on="Service_Name", how="left")

    if df.empty:
        return None, None, None, None

    policy = Policy.objects(
        policy_number=df["ContractorClientPolicyNumber"].iloc[0]
    ).first()
    if not policy:
        policy = Policy.objects(
            policy_number=df["ContractorClientPolicyNumber2"].iloc[0]
        ).first()

    vip_level = normalize_text(df["Contract"].iloc[0])
    selected = [
        c for c in policy.coverage_details if normalize_text(c.vip_level) == vip_level
    ]

    if not selected:
        available_levels = [c.vip_level for c in policy.coverage_details]
        return df, policy, None, available_levels

    detail = selected[0].to_mongo().to_dict()
    return df, policy, detail, None


@app.route("/", methods=["GET", "POST"])
def home():
    if request.method == "POST":
        visit_id = request.form.get("visit_id")
        if visit_id:
            return redirect(url_for("visit_detail", visit_id=visit_id))
    return render_template("index.html")


@app.route("/visit/<visit_id>")
def visit_detail(visit_id):
    df, policy, detail, available_levels = get_visit_data(visit_id)

    if df is None:
        return render_template("error.html", message="Visit ID not found")

    if detail is None:
        return render_template(
            "error.html",
            message=f"No information found for class {df['Contract'].iloc[0]}.",
            available_levels=available_levels,
        )

    # Store data in session for chat route
    session[f"visit_data_{visit_id}"] = {
        "df": df.to_json(),
        "policy_number": policy.policy_number,
        "detail": json.dumps(detail, default=str),
    }

    return render_template(
        "index.html",
        selected_visit=visit_id,
        df=df.to_dict(orient="records"),
        policy=policy,
        detail=detail,
    )


@app.route("/chat/<visit_id>", methods=["GET", "POST"])
def chat(visit_id):
    # Try to get cached data from session first
    cached_data = session.get(f"visit_data_{visit_id}")

    if cached_data:
        df = pd.read_json(cached_data["df"])
        policy = Policy.objects(policy_number=cached_data["policy_number"]).first()
        detail = json.loads(cached_data["detail"])
    else:
        # Fetch if not in session
        df, policy, detail, available_levels = get_visit_data(visit_id)

        if df is None:
            return render_template("error.html", message="Visit ID not found")

        if detail is None:
            return jsonify({"error": "No coverage found."})

    if request.method == "POST":
        user_input = request.form.get("message")
        visit_info = str(
            df[["Med_Dept", "Specialty_Name", "Diagnose_Name", "ICD10 Code"]]
            .iloc[0]
            .to_dict()
        ) + str(df[["Service_Name", "Price"]].to_dict(orient="records"))
        assistant_reply = llm_response(str(detail), visit_info, user_input)
        return jsonify({"response": assistant_reply})

    return render_template(
        "chat.html", visit_id=visit_id, df=df.to_dict(orient="records"), policy=policy
    )


if __name__ == "__main__":
    app.run(debug=True)
