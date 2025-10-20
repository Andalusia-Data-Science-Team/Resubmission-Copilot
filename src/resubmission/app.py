import streamlit as st
import pandas as pd
from resubmission.models import Policy
from resubmission.utils import llm_response, normalize_text

df = pd.read_excel(
    "/home/ai/Workspace/Nadine/Resubmission-Copilot/Data/resub_phase2_bupa_sample.xlsx",
    parse_dates=["Start_Date"],
)
sf = pd.read_csv("/home/ai/Workspace/Nadine/Resubmission-Copilot/Data/sfda_list.csv")
sf = sf.rename(columns={"NameEn": "Service_Name"})
df = df.drop_duplicates(keep="last")
df["ContractorClientPolicyNumber"] = df["ContractorClientPolicyNumber"].astype(str)
df["ContractorClientPolicyNumber2"] = df["ContractorClientPolicyNumber2"].astype(str)
df["Contract"] = (
    df["Contract"]
    .astype(str)
    .str.split("-", n=1)
    .pipe(lambda p: p.str[1].str.strip().fillna(p.str[0].str.strip()))
)
df = df.rename(columns={"ResponseSubmitted": "Price"})
df = pd.merge(df, sf, on="Service_Name", how="left")

st.title("Smart Search - AI Policy Finder")

visit_id = st.selectbox("Visit ID", options=df["VisitID"].unique(), index=None)

if not visit_id:
    st.info("Select a Visit ID to Display Policy Details")

else:
    sub = df[df["VisitID"] == visit_id].reset_index(drop=True)
    st.dataframe(sub.drop("ContractorClientPolicyNumber2", axis=1))

    policy = Policy.objects(
        policy_number=sub["ContractorClientPolicyNumber"].iloc[0]
    ).first()
    if not policy:
        policy = Policy.objects(
            policy_number=sub["ContractorClientPolicyNumber2"].iloc[0]
        ).first()

    st.subheader(f"{policy.company_name} - {policy.policy_holder}")
    st.caption(
        f"Effective From: {policy.effective_from} | Effective To: {policy.effective_to}"
    )

    vip_level = normalize_text(sub["Contract"].iloc[0])

    # --- Step 4: Display results ---
    feature_on = st.toggle("Resubmission AI Assistant")
    try:
        selected = [
            c
            for c in policy.coverage_details
            if normalize_text(c.vip_level) == vip_level
        ]
        detail = selected[0].to_mongo().to_dict()
    except Exception:
        st.error(
            f"⚠️ No information found for this patient's class '{sub['Contract'].iloc[0]}'"
        )
        available_levels = [c.vip_level for c in policy.coverage_details]
        st.warning(f"Available Classes: {available_levels}")
        st.stop()
    if not feature_on:
        always_show = ["overall_annual_limit", "special_instructions"]

        # Display the always-show fields first (if they exist)
        for field in always_show:
            value = detail.get(field)
            if value:
                label = field.replace("_", " ").title()
                with st.expander(label, expanded=False):  # collapsed by default
                    st.write(value)

        # Prepare dropdown fields (everything else, sorted and prettified)
        fields = [k for k in detail.keys() if k not in always_show and k != "vip_level"]
        fields_sorted = sorted(fields)

        # Map pretty labels to actual field keys
        label_map = {k.replace("_", " ").title(): k for k in fields_sorted}
        labels = list(label_map.keys())

        # Dropdown to select one field at a time
        selected_label = st.selectbox("Coverage Details", options=labels)
        field = label_map[selected_label]

        # Display selected field in a card-style box
        st.markdown(
            f"""
            <div style="
                background-color:#f8f9fa;
                border-radius:10px;
                padding:20px;
                margin-top:10px;
                border:1px solid #ddd;
            ">
                <h4 style="margin-bottom:5px;">{selected_label}</h4>
                <p style="font-size:16px;">{detail.get(field, 'Not specified')}</p>
            </div>
            """,
            unsafe_allow_html=True,
        )
    else:
        if "prev_visit_id" not in st.session_state:
            st.session_state["prev_visit_id"] = visit_id

        # If user selected a new visit, reset chat history
        if visit_id != st.session_state["prev_visit_id"]:
            st.session_state["messages"] = []  # clear chat
            st.session_state["prev_visit_id"] = visit_id

        # A place to store chat history in session state
        if "messages" not in st.session_state:
            st.session_state["messages"] = []

        # Chat input
        user_input = st.chat_input("Type your message here...")

        if user_input:
            # Save user message
            st.session_state["messages"].append({"role": "user", "content": user_input})
            # Save assistant (preview) message
            visit = str(
                sub[["Med_Dept", "Specialty_Name", "Diagnose_Name", "ICD10 Code"]]
                .iloc[0]
                .to_dict()
            ) + str(sub[["Service_Name", "Price"]].to_dict(orient="records"))
            st.session_state["messages"].append(
                {
                    "role": "assistant",
                    "content": llm_response(str(detail), visit, user_input),
                }
            )

        # Display chat history
        for msg in st.session_state["messages"]:
            if msg["role"] == "user":
                with st.chat_message("user"):
                    st.markdown(msg["content"])
            else:
                with st.chat_message("assistant"):
                    st.markdown(msg["content"])
