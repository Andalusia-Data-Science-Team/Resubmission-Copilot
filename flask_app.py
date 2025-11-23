from flask import Flask, render_template, request, redirect, url_for, jsonify, session , render_template_string
from pymongo.errors import ServerSelectionTimeoutError
import pandas as pd
from resubmission.const import INDEX
# from resubmission.models import Policy
from resubmission.utils import (
    get_visits_by_date,
    get_visit_data,
    get_policy_details,
    llm_response,
    generate_justification)
import json
from flask_session import Session
from datetime import timedelta
from io import StringIO

app = Flask(__name__)
app.config['SESSION_TYPE'] = 'filesystem'  # or 'redis'
app.permanent_session_lifetime = timedelta(hours=2)
Session(app)
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
                session["last_search"] = {
                    "start_date": start_date,
                    "end_date": end_date,
                    "visit_ids": visit_ids,
                }
            else:
                return render_template(
                    INDEX,
                    error_message=f"No Bupa visits were found between {start_date} and {end_date}. Please try different dates.",
                    error_type="warning",
                )

        # Visit selection (after date search was done)
        elif visit_id:
            return redirect(url_for("display_policy_details", visit_id=visit_id))

    return render_template(
        INDEX,
        visit_ids=visit_ids,
        show_dropdown=show_dropdown,
        start_date=start_date,
        end_date=end_date,
    )


@app.route("/visit/<visit_id>", methods=["GET", "POST"])
def display_policy_details(visit_id):
    df = get_visit_data(visit_id)
    if request.method == "POST":
        data = {"start_date": request.form.get("start_date"), "end_date": request.form.get("end_date")}

        # Render a hidden form that auto-submits as POST to "/"
        return render_template_string("""
            <form id="redirForm" method="POST" action="{{ url_for('home') }}">
                {% for key, val in data.items() %}
                    <input type="hidden" name="{{ key }}" value="{{ val }}">
                {% endfor %}
            </form>
            <script>document.getElementById('redirForm').submit();</script>
        """, data=data)
    if df is None:
        return render_template(
            "error.html", message="No BE or CV Rejections Were Found for This Visit"
        )

    try:
        policy, detail, available_levels = get_policy_details(df)
    except ServerSelectionTimeoutError:
        # MongoDB is unreachable; show a friendly error page instead of a 500
        return render_template(
            "error.html",
            message=(
                "Cannot reach the MongoDB server at the configured host:27017. "
                "Please check the MongoDB server, its bindIp and firewall rules."
            ),
        )
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
    last_search = session.get("last_search", {})
    visit_ids = last_search.get("visit_ids", [])
    start_date = last_search.get("start_date")
    end_date = last_search.get("end_date")
    show_dropdown = bool(visit_ids)

    # display policy details
    return render_template(
        INDEX,
        selected_visit=visit_id,
        df=df.to_dict(orient="records"),
        policy=policy,
        detail=detail,
        visit_ids=visit_ids,
        show_dropdown=show_dropdown,
        start_date=start_date,
        end_date=end_date,
    )


@app.route("/chat/<visit_id>", methods=["GET", "POST"])
def chat(visit_id):
    cached_data = session.get(f"visit_data_{visit_id}")
    df = pd.read_json(StringIO(cached_data["df"]))
    detail = json.loads(cached_data["detail"])

    # Handle POST requests (chat messages or justification)
    if request.method == "POST":
        # Case 1: Chat message (form submission)
        if request.content_type == "application/x-www-form-urlencoded":
            user_input = request.form.get("message")
            visit_info = str(
                df[["Med_Dept", "Specialty_Name", "Diagnose_Name", "ICD10 Code"]]
                .iloc[0]
                .to_dict()
            ) + str(df[["Service_Name", "Price"]].to_dict(orient="records"))

            assistant_reply = llm_response(str(detail), visit_info, user_input)
            return jsonify({"response": assistant_reply})

        # Case 2: Generate Justification (button click)
        elif request.content_type == "application/json":
            data = request.get_json()
            justification_text = generate_justification(data, str(detail))
            return jsonify({"justification": justification_text})

    # GET request — render the chat page
    return render_template(
        "chat.html",
        visit_id=visit_id,
        df=df.to_dict(orient="records"),
    )


if __name__ == "__main__":
    app.run(host='0.0.0.0', port=2199, debug=True)
