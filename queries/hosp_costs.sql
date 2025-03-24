CREATE OR REPLACE TABLE hosp_costs as (
  
  WITH franklin_square as (
    SELECT DISTINCT
        description
      , "code|1"
      , "code|1|type"
      , "code|3"
      , "code|3|type"
      , setting
      , billing_class
      , "standard_charge|gross"
      , "standard_charge|min"
      , "standard_charge|max"
      , "standard_charge|discounted_cash"
      , 'franklin_square' as hosp_name
      , filename
    FROM read_csv('https://www.medstarhealth.org/-/media/project/mho/medstar/billing-and-insurance/2025/520608007_medstarfranklinsquaremedicalcenter_standardcharges.csv', skip=2, sample_size = -1, filename=TRUE))

  , georgetown_univ as (
     SELECT
        description
      , "code|1"
      , "code|1|type"
      , "code|3"
      , "code|3|type"
      , setting
      , billing_class
      , "standard_charge|gross"
      , "standard_charge|min"
      , "standard_charge|max"
      , "standard_charge|discounted_cash"
      , 'georgetown_univ' as hosp_name
      , filename
    FROM read_csv('https://www.medstarhealth.org/-/media/project/mho/medstar/billing-and-insurance/2025/522218584_medstargeorgetownuniversityhospital_standardcharges.csv', skip=2, sample_size = -1, filename=TRUE))

  , good_samaritan as (
      SELECT 
          description
        , "code|1"
        , "code|1|type"
        , "code|3"
        , "code|3|type"
        , setting
        , billing_class
        , "standard_charge|gross"
        , "standard_charge|min"
        , "standard_charge|max"
        , "standard_charge|discounted_cash"
        , 'good_samaritan' as hosp_name
        , filename
      FROM read_csv('https://www.medstarhealth.org/-/media/project/mho/medstar/billing-and-insurance/2025/520591607_medstargoodsamaritan_standardcharges.csv', skip=2, sample_size = -1, filename=TRUE))

  , harbor_hosp as (
      SELECT 
          description
        , "code|1"
        , "code|1|type"
        , "code|3"
        , "code|3|type"
        , setting
        , billing_class
        , "standard_charge|gross"
        , "standard_charge|min"
        , "standard_charge|max"
        , "standard_charge|discounted_cash"
        , 'harbor_hosp' as hosp_name
        , filename
      FROM read_csv('https://www.medstarhealth.org/-/media/project/mho/medstar/billing-and-insurance/2025/520491660_medstarharborhospital_standardcharges.csv', skip=2, sample_size = -1, filename=TRUE) 
)

  , montgomery_med as (
        SELECT 
          description
        , "code|1"
        , "code|1|type"
        , "code|3"
        , "code|3|type"
        , setting
        , billing_class
        , "standard_charge|gross"
        , "standard_charge|min"
        , "standard_charge|max"
        , "standard_charge|discounted_cash"
        , 'montgomery_med' as hosp_name
        , filename
      FROM read_csv('https://www.medstarhealth.org/-/media/project/mho/medstar/billing-and-insurance/2025/520646893_medstarmontgomerymedicalcenter_standardcharges.csv', skip=2, sample_size = -1, filename=TRUE) 
  )
  , national_rehab as (
        SELECT 
          description
        , "code|1"
        , "code|1|type"
        , "code|3"
        , "code|3|type"
        , setting
        , billing_class
        , "standard_charge|gross"
        , "standard_charge|min"
        , "standard_charge|max"
        , "standard_charge|discounted_cash"
        , 'national_rehab' as hosp_name
        , filename
      FROM read_csv('https://www.medstarhealth.org/-/media/project/mho/medstar/billing-and-insurance/2025/521369749_medstarnationalrehabilitationhospital_standardcharges.csv', skip=2, sample_size = -1, filename=TRUE) 
  )

  , s_maryland as (
        SELECT 
          description
        , "code|1"
        , "code|1|type"
        , "code|3"
        , "code|3|type"
        , setting
        , billing_class
        , "standard_charge|gross"
        , "standard_charge|min"
        , "standard_charge|max"
        , "standard_charge|discounted_cash"
        , 's_maryland' as hosp_name
        , filename
      FROM read_csv('https://www.medstarhealth.org/-/media/project/mho/medstar/billing-and-insurance/2025/460726303_medstarsouthernmarylandhospitalcenter_standardcharges.csv', skip=2, sample_size = -1, filename=TRUE) 
  )

  , mary_hosp as (
        SELECT 
          description
        , "code|1"
        , "code|1|type"
        , "code|3"
        , "code|3|type"
        , setting
        , billing_class
        , "standard_charge|gross"
        , "standard_charge|min"
        , "standard_charge|max"
        , "standard_charge|discounted_cash"
        , 'mary_hosp' as hosp_name
        , filename
      FROM read_csv('https://www.medstarhealth.org/-/media/project/mho/medstar/billing-and-insurance/2025/520619006_medstarstmaryshospital_standardcharges.csv', skip=2, sample_size = -1, filename=TRUE) 
  )
  
  , union_memorial as (
        SELECT 
          description
        , "code|1"
        , "code|1|type"
        , "code|3"
        , "code|3|type"
        , setting
        , billing_class
        , "standard_charge|gross"
        , "standard_charge|min"
        , "standard_charge|max"
        , "standard_charge|discounted_cash"
        , 'union_memorial' as hosp_name
        , filename
      FROM read_csv('https://www.medstarhealth.org/-/media/project/mho/medstar/billing-and-insurance/2025/520591685_medstarunionmemorialhospital_standardcharges.csv', skip=2, sample_size = -1, filename=TRUE) 
  )

  , washington_hosp_center as (
        SELECT 
          description
        , "code|1"
        , "code|1|type"
        , "code|3"
        , "code|3|type"
        , setting
        , billing_class
        , "standard_charge|gross"
        , "standard_charge|min"
        , "standard_charge|max"
        , "standard_charge|discounted_cash"
        , 'washington_hosp_center' as hosp_name
        , filename
      FROM read_csv('https://www.medstarhealth.org/-/media/project/mho/medstar/billing-and-insurance/2025/521272129_medstarwashingtonhospitalcenter_standardcharges.csv', skip=2, sample_size = -1, filename=TRUE) 
  )
  
, comb as (
  SELECT * FROM franklin_square UNION
  SELECT * FROM georgetown_univ UNION
  SELECT * FROM good_samaritan UNION
  SELECT * FROM harbor_hosp UNION
  SELECT * FROM montgomery_med UNION
  SELECT * FROM national_rehab UNION
  SELECT * FROM s_maryland UNION
  SELECT * FROM mary_hosp UNION
  SELECT * FROM union_memorial UNION
  SELECT * FROM washington_hosp_center
)

SELECT * FROM comb WHERE "code|3" IS NOT NULL
)