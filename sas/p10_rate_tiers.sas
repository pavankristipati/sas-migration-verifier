/* p10_rate_tiers.sas
   Loans grouped into interest-rate tiers using a SAS format, by product. */

%let path = /home/&sysuserid/lab;
%let size = 1k;
%let copy = practice;

data loans;
  infile "&path/data/&size/&copy/loans.csv" dsd firstobs=2 truncover;
  length loan_id $12 customer_id $10 product $12 branch $12;
  input loan_id $ customer_id $ product $ branch $
        origination_date :yymmdd10. original_amount interest_rate;
  format origination_date yymmdd10.;
run;

data payments;
  infile "&path/data/&size/&copy/payments.csv" dsd firstobs=2 truncover;
  length loan_id $12;
  input loan_id $ month_end :yymmdd10. balance days_past_due;
  format month_end yymmdd10.;
run;

proc format;
  value ratetier
    low  -< 5    = 'Low'
    5    -< 12   = 'Mid'
    12   - high  = 'High'
    other        = 'Unknown';
run;

data tiered;
  set loans;
  length rate_tier $8;
  rate_tier = put(interest_rate, ratetier.);
run;

proc sql;
  create table result as
  select product, rate_tier,
         count(*)                       as loans,
         round(mean(interest_rate), 0.001) as avg_rate format=8.3
  from tiered
  group by product, rate_tier
  order by product, rate_tier;
quit;

proc export data=result outfile="&path/out/p10_&size._&copy..csv"
            dbms=csv replace;
run;
