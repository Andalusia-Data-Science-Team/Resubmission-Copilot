from flask import Flask, render_template, request, redirect, url_for, jsonify, session
import pandas as pd
from resubmission.models import Policy
from resubmission.utils import get_visits_by_date, get_visit_data, get_policy_details, llm_response
import json

app = Flask(__name__)
app.secret_key = "my-secret-key"


@app.route("/", methods=["GET", "POST"])
def home():
    visit_ids = []
    show_dropdown = False
    start_date = None
    end_date = None

    if request.method == "POST":
        start_date = request.form.get("start_date")
        end_date = request.form.get("end_date")
        visit_id = request.form.get("visit_id")

        # Date search takes priority (if start_date exists, it's the date form)
        if start_date and end_date:
            visit_ids = get_visits_by_date(start_date, end_date)

            if visit_ids is not None and not visit_ids.empty:
                show_dropdown = True
                visit_ids = visit_ids.tolist()

                # Store in session for persistence
                session['last_search'] = {
                    'start_date': start_date,
                    'end_date': end_date,
                    'visit_ids': visit_ids
                }
            else:
                return render_template(
                    "index.html",
                    error_message=f"No Bupa visits were found between {start_date} and {end_date}. Please try different dates.",
                    error_type="warning",
                )

        # Visit selection (after date search was done)
        elif visit_id:
            return redirect(url_for("display_policy_details", visit_id=visit_id))

    return render_template(
        "index.html",
        visit_ids=visit_ids,
        show_dropdown=show_dropdown,
        start_date=start_date,
        end_date=end_date
    )


@app.route("/visit/<visit_id>")
def display_policy_details(visit_id):
    df = get_visit_data(visit_id)
    if df is None:
        return render_template("error.html", message="No BE or CV Rejections Were Found for This Visit")

    policy, detail, available_levels = get_policy_details(df)
    if detail is None:
        return render_template(
            "error.html",
            message=f"No information found for class {df['Contract'].iloc[0]}.",
            available_levels=available_levels,
        )

    # Store data in session for the chat route
    session[f"visit_data_{visit_id}"] = {
        "df": df.to_json(),
        "policy_number": policy.policy_number,
        "detail": json.dumps(detail, default=str),
    }

    # Retrieve last search data from session
    last_search = session.get('last_search', {})
    visit_ids = last_search.get('visit_ids', [])
    start_date = last_search.get('start_date')
    end_date = last_search.get('end_date')
    show_dropdown = bool(visit_ids)

    # display policy details
    return render_template(
        "index.html",
        selected_visit=visit_id,
        df=df.to_dict(orient="records"),
        policy=policy,
        detail=detail,
        visit_ids=visit_ids,
        show_dropdown=show_dropdown,
        start_date=start_date,
        end_date=end_date
    )


@app.route("/chat/<visit_id>", methods=["GET", "POST"])
def chat(visit_id):
    # Get cached data from session that was stored in visit detail route
    cached_data = session.get(f"visit_data_{visit_id}")
    df = pd.read_json(cached_data["df"])
    policy = Policy.objects(policy_number=cached_data["policy_number"]).first()
    detail = json.loads(cached_data["detail"])

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
