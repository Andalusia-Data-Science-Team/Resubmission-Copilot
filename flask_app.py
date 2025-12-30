import json
import logging
import os
from datetime import timedelta
from io import StringIO

import pandas as pd
from dotenv import load_dotenv
from flask import (
    Flask,
    jsonify,
    redirect,
    render_template,
    render_template_string,
    request,
    session,
    url_for,
)
from pymongo.errors import ServerSelectionTimeoutError

from flask_session import Session  # type: ignore
from src.resubmission.chatbot import get_agent_response
from src.resubmission.const import ERROR, INDEX
from src.resubmission.utils import (
    get_policy_details,
    get_visit_data,
    get_visits_by_date,
)

load_dotenv()

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
formatter = logging.Formatter("%(asctime)s | %(levelname)s | %(message)s")
file_handler = logging.FileHandler("app.log", mode="a")
file_handler.setFormatter(formatter)
logger.addHandler(file_handler)

app = Flask(__name__)
app.config["SESSION_TYPE"] = "filesystem"
app.permanent_session_lifetime = timedelta(hours=1)
Session(app)
app.secret_key = os.getenv("FLASK_SECRET_KEY")


@app.route("/", methods=["GET", "POST"])
def home():
    visit_ids = get_visits_by_date()

    if request.method == "POST":

        visit_id = request.form.get("visit_id")
        if visit_id:
            return redirect(url_for("display_policy_details", visit_id=visit_id))
        else:
            return render_template(
                INDEX,
                error_message="No Bupa visit id. Please check db connection.",
                error_type="warning",
            )

    return render_template(
        INDEX,
        visit_ids=visit_ids,
    )


@app.route("/visit/<visit_id>", methods=["GET", "POST"])
def display_policy_details(visit_id):
    df = get_visit_data(visit_id, logger)
    
    if request.method == "POST":
        data = {
            "start_date": request.form.get("start_date"),
            "end_date": request.form.get("end_date"),
        }

        # Render a hidden form that auto-submits as POST to "/"
        return render_template_string(
            """
            <form id="redirForm" method="POST" action="{{ url_for('home') }}">
                {% for key, val in data.items() %}
                    <input type="hidden" name="{{ key }}" value="{{ val }}">
                {% endfor %}
            </form>
            <script>document.getElementById('redirForm').submit();</script>
        """,
            data=data,
        )
    if df is None:
        return render_template(
            ERROR, message="No BE or CV Rejections Were Found for This Visit"
        )

    try:
        selected_level = session.pop("tmp_level", None)
        if selected_level:
            df['Contract'] = selected_level
        policy, detail, available_levels = get_policy_details(df, logger)
    except ServerSelectionTimeoutError:
        # MongoDB is unreachable; show a friendly error page instead of a 500
        return render_template(
            ERROR,
            message=(
                "Cannot reach the MongoDB server at the configured host:27017. "
                "Please check the MongoDB server, its bindIp and firewall rules."
            ),
        )
    if policy is None:
        return render_template(
            ERROR,
            message=f"No information found for policy {df["ContractorClientPolicyNumber"].iloc[0]} {df["ContractorClientEnName"].iloc[0]}.",
        )
    if detail is None:
        return render_template(
            ERROR,
            message=f"No information found for class {df['Contract'].iloc[0]}.",
            available_levels=available_levels,
            visit_id=visit_id,
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

@app.route("/select_level/<visit_id>", methods=["POST"])
def select_level(visit_id):
    # store selected level temporarily
    session["tmp_level"] = request.form.get("selected_level")
    
    # redirect back to display_policy_details
    return redirect(url_for("display_policy_details", visit_id=visit_id))

@app.route("/chat/<visit_id>", methods=["GET", "POST"])
def chat(visit_id):
    cached_data = session.get(f"visit_data_{visit_id}")
    if cached_data:
        df = pd.read_json(StringIO(cached_data["df"]))
        detail = json.loads(cached_data["detail"])

    # Handle POST requests (chat messages or justification)
    if request.method == "POST":
        thread_id = str(getattr(session, "sid", None))
        visit_info = str(
            df[["Med_Dept", "Specialty_Name", "Diagnose_Name", "ICD10 Code"]]
            .iloc[0]
            .to_dict()
        ) + str(df[["Service_Name", "Price"]].to_dict(orient="records"))
        # Case 1: Chat message (form submission)
        if request.content_type == "application/x-www-form-urlencoded":
            user_input = request.form.get("message")

            assistant_reply = get_agent_response(
                user_input, thread_id, str(detail), visit_info
            )
            return jsonify({"response": assistant_reply})

        # Case 2: Generate Justification (button click)
        elif request.content_type == "application/json":
            service = request.get_json()
            justification_text = get_agent_response(
                None, thread_id, str(detail), visit_info, service
            )
            return jsonify({"justification": justification_text})

    # GET request — render the chat page
    return render_template(
        "chat.html",
        visit_id=visit_id,
        df=df.to_dict(orient="records"),
    )


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=2200, debug=True)
