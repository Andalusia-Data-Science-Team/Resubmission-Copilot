SELECT VisitID
FROM [VisitMgt].[VisitFinincailInfo]
WHERE CreatedDate >= ?
AND CreatedDate < DATEADD(DAY, 1, ?)
AND ContractorEnName = 'Bupa'
ORDER BY CreatedDate;