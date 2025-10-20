from mongoengine import (
    connect,
    Document,
    EmbeddedDocument,
    StringField,
    DateField,
    EmbeddedDocumentListField,
)
from resubmission.config_handler import config

# 1. Connect to MongoDB
params = config(section="mongodb")
connect(
    db=params["db"],
    host=params.get("host"),
    port=int(params.get("port")),
    username=params.get("username"),
    password=params.get("password"),
    authentication_source=params.get("authentication_source"),
)


# 2. Define EmbeddedDocument for coverage details
class CoverageDetail(EmbeddedDocument):
    vip_level = StringField()
    overall_annual_limit = StringField()
    inpatient_outpatient_treatment = StringField()
    accommodation = StringField()
    outpatient_deductible_mpn = StringField()
    outpatient_deductible_hospitals = StringField()
    outpatient_deductible_polyclinic = StringField()
    branded_medication_deductible = StringField()
    generic_medication_deductible = StringField()
    network = StringField()
    std = StringField()
    menopausal = StringField()
    post_menopausal = StringField()
    premature_babies_treatment = StringField()
    checkup = StringField()
    vaccination = StringField()
    optical_frame = StringField()
    birth_control = StringField()
    obesity_surgery_bmi_over_35 = StringField()
    obesity_surgery_bmi_over_40 = StringField()
    kidney_transplant = StringField()
    bone_marrow_transplant = StringField()
    organ_transplant = StringField()
    separate_plan_limit = StringField()
    neonatal_screening = StringField()
    psychiatric = StringField()
    dialysis = StringField()
    hearing_aids_audiometry = StringField()
    dental_general = StringField()
    dental_corrective = StringField()
    dental_emergency = StringField()
    neo_natal_care = StringField()
    circumcision = StringField()
    acquired_heart_valves_disease = StringField()
    newborn_disability_screening = StringField()
    alzheimers = StringField()
    congenital = StringField()
    maternity = StringField()
    optical = StringField()
    autism = StringField()
    ear_piercing = StringField()
    screening = StringField()
    disability_cases = StringField()
    donor_organ_harvesting = StringField()
    physiotherapy = StringField()
    approval_preauthorization_notes = StringField()
    special_instructions = StringField()


# 3. Define Main Document
class Policy(Document):
    policy_number = StringField(required=True)
    company_name = StringField()
    policy_holder = StringField()
    effective_from = DateField()
    effective_to = DateField()
    coverage_details = EmbeddedDocumentListField(CoverageDetail)
