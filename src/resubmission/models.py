from mongoengine import (
    DateField,
    Document,
    EmbeddedDocument,
    EmbeddedDocumentListField,
    StringField,
    connect,
)

from src.resubmission.config_handler import config

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


###########################################
# NCCI Policy Model
###########################################
class CaseCoverage(EmbeddedDocument):
    case_name = StringField(required=True)
    patient_share = StringField(required=True)
    max_patient_share = StringField(required=True)
    max_consultation_fee = StringField(required=True)
    approval_threshold = StringField(required=True)

class SubCoverage(EmbeddedDocument):
    sub_coverage_code = StringField(required=True)
    description = StringField(required=True)
    limit = StringField(null=True)
    approval_threshold = StringField(null=True)

class Benefit(EmbeddedDocument):
    benefit_code = StringField(required=True)
    description = StringField(required=True)
    limit = StringField(required=True)

    cases = EmbeddedDocumentListField(CaseCoverage, null=True)
    sub_coverages = EmbeddedDocumentListField(SubCoverage, null=True)

class PolicyClass(EmbeddedDocument):
    class_code = StringField(required=True)
    class_limit = StringField(null=True)

    room_type = StringField(required=True)
    room_limit = StringField(required=True)

    benefits = EmbeddedDocumentListField(Benefit, null=True)

class Endorsement(EmbeddedDocument):
    number = StringField(required=True)
    date = StringField(required=True)  # keep string to match JSON schema
    type = StringField(required=True)
    message = StringField(required=True)

class NCCI_Policy(Document):
    provider_name = StringField(required=True)
    policy_number = StringField(required=True, unique=True)
    policy_status = StringField(required=True)
    policy_holder_name = StringField(required=True)
    policy_type = StringField(required=True)

    issue_date = DateField()
    start_date = DateField()
    end_date = DateField()
    last_update = DateField()

    coverage = StringField(null=True)
    exclusion = StringField(null=True)
    comments = StringField(null=True)

    classes = EmbeddedDocumentListField(PolicyClass, required=True)

    endorsements = EmbeddedDocumentListField(Endorsement, null=True)
    additional_information = StringField(null=True)
