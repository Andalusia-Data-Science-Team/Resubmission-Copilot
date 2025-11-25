WITH CTE AS (

            SELECT 
                ID,
                 DENSE_RANK() OVER (PARTITION BY VisitID, StatementID ORDER BY CreatedDate DESC) AS DR
            FROM Nphies.ClaimTransaction
            WHERE TransactionType = 'Request'

    ) 
SELECT 
	   V.ID AS VisitID,
	   V.CreatedDate AS Start_Date ,
	   VC.EnName AS Med_Dept,
	   V.MainSpecialityEnName AS Specialty_Name,
	   CAST(VFI.ContractorClientPolicyNumber AS NVARCHAR(20)) AS ContractorClientPolicyNumber,
	   VFI.ContractorClientEnName,
        CASE  
            WHEN VFI.ContractEnName LIKE '%OPD%' OR VFI.ContractEnName LIKE '%IPD%'
                THEN LTRIM(SUBSTRING(
                        VFI.ContractEnName,
                        CASE
                            WHEN CHARINDEX('OPD', VFI.ContractEnName) > CHARINDEX('IPD', VFI.ContractEnName)
                                THEN CHARINDEX('OPD', VFI.ContractEnName)
                            ELSE CHARINDEX('IPD', VFI.ContractEnName)
                        END,
                        LEN(VFI.ContractEnName)
                    ))
            WHEN VFI.ContractEnName LIKE '%VIP%'
                THEN LTRIM(SUBSTRING(VFI.ContractEnName, CHARINDEX('VIP', VFI.ContractEnName), LEN(VFI.ContractEnName)))
            WHEN RIGHT(LTRIM(RTRIM(VFI.ContractEnName)), 2) = 'A+' THEN 'A+'
            WHEN RIGHT(LTRIM(RTRIM(VFI.ContractEnName)), 3) = 'SNB' THEN 'SNB'
            WHEN RIGHT(LTRIM(RTRIM(VFI.ContractEnName)), 2) IN (' A', ' B')
                THEN RIGHT(LTRIM(RTRIM(VFI.ContractEnName)), 1)
            ELSE VFI.ContractEnName
        END AS [Contract],

	   CI.NameEn AS Service_Name,
	   P.ISDRUG,
	   CI.ResponseReasonCode ,
	   CI.ResponseReason,
	   CI.ResponseSubmitted AS Price,
       PCD.ICDDiagnoseNames AS Diagnose_Name,
       PCD.ICDDiagnoseCodes AS 'ICD10 Code'


FROM Nphies.ClaimTransaction CT
RIGHT JOIN CTE
	ON CTE.ID=CT.ID AND CTE.DR=1
LEFT JOIN  Nphies.ClaimItem CI 
	ON CI.ClaimTransactionID=CTE.Id
LEFT JOIN VISITMGT.Visit V
	ON V.ID=CT.VisitId
LEFT JOIN VISITMGT.SLKP_visitclassification VC 
	ON V.VisitClassificationID = VC.ID
LEFT JOIN VisitMgt.VisitFinincailInfo VFI
	ON VFI.VisitID=V.ID
LEFT JOIN (SELECT VISITID,
STRING_AGG(PCD.ICDDiagnoseName, ' , ') AS ICDDiagnoseNames,
STRING_AGG(PCD.ICDDiagnoseCode, ' , ') AS ICDDiagnoseCodes,
STRING_AGG(PC.Note, ' , ')            AS Problem_Note
                   
FROM Patprlm.ProblemCard AS PC
LEFT JOIN Patprlm.ProblemCardDetail PCD  ON PC.ID = PCD.ProblemCardID  where PC.IsDeleted=0 GROUP BY VISITID
) AS PCD  ON PCD.VisitID = V.ID
LEFT JOIN PMGT.[Product] P
	ON P.ID=CI.ITEMID
WHERE 	 ( CI.ResponseReasonCode LIKE '%BE-%' 
		OR CI.ResponseReasonCode LIKE '%CV-%'   
		OR CI.ResponseReason LIKE '%CV-%'
		OR CI.ResponseReason LIKE '%BE-%'
	     )
AND CT.VisitId = ?
