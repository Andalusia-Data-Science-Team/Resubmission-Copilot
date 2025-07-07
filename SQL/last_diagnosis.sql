SELECT DISTINCT
	FB.Organization_Key,
	FB.Service_Date,
	FB.Episode_key,
	FB.patient_id,
	P.English_Name AS PatientName,
	CN.Title AS Title_Note,
	CN.Note,
	CN.Action,
	CR.EnName AS NotesCancelReason,
	NS.EnName AS NotesStatus,
	NT.EnName AS NotesType,
	BMI.Height,
	BMI.Weight,
	BMI.MinWeight,
	BMI.MaxWeight,
	BMI.TargetWeight,
	BMI.BMIValue,
	BMI.Status_EN AS BMI_StatusEN,
	BMI.Status_AR AS BMI_StatusAR,
	VS.Value1 AS Vital_Sign1,
	RV.MinValue1 AS MinVital_Sign1,
	RV.MaxValue1 AS MaxVital_Sign1,
	VS.Value2 AS Vital_Sign2,
	RV.MinValue2 AS MinVital_Sign2,
	RV.MaxValue2 AS MaxVital_Sign2,
	VST.UnitOfMeasure,
	VST.EnName AS Vital_SignType,
	VST.EnShortName AS ShortVital_SignType,
	DD.DiagnoseName,
	DD.DiagnosisParent_Desc,
	DD.DiseaseID,
	DD.ICDDiagnoseCode,
	P.[Chronic Status],
	P.Marital_Status,
	P.Age,
	P.Gender_Description,
	DCS.ChiefComplaintNotes,
	DCS.SymptomNotes


FROM DAX.FactBilling FB
	LEFT JOIN dax.DimClinicalNotes CN
	ON CN.Episode_Key = FB.Episode_key
		LEFT JOIN [dax].[DimNotesCancelReason] CR
			ON CN.CancelReasonID = CR.ID
		LEFT JOIN [dax].[DimNotesStatus] NS
			ON CN.StatusID = NS.ID
		LEFT JOIN [dax].[DimNotesType] NT
			ON CN.TypeID = NT.ID
	LEFT JOIN dax.DimBMI BMI
		ON FB.EPISODE_KEY = BMI.EPISODE_KEY
	LEFT JOIN dax.Dim_VitalSign VS
	   	ON FB.Episode_key = VS.Episode_Key 
		LEFT JOIN dax.Dim_VitalSign_RangeValues RV
			ON VS.VitalSignRangeID = RV.VitalSignRangeID
		LEFT JOIN dax.Dim_VitalSign_Type VST
			ON VS.VitalSignType_ID = VST.VitalSignType_ID
	LEFT JOIN dax.DimDiagnosisN DD
		ON FB.Episode_key = DD.Episode_Key
	LEFT JOIN DAX.DimPatient P 
		ON FB.patient_id = P.PATIENT_ID
	LEFT JOIN DAX.DimChiefComplaint_Symptoms DCS
		ON FB.Episode_key = DCS.VisitID
WHERE FB.Organization_Key = 1 
AND FB.DATEKEY = 20250629