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
  , hosp_name
  , filename
  
FROM main.hosp_costs

WHERE "code|3" = '47000'
