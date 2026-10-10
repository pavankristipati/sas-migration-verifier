/* p06_loan_age.sas
   Loan age in months as of Sep 30, 2026, grouped into age buckets, by product. */

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

data aged;
  set loans;
  age_months = intck('month', origination_date, '30SEP2026'd);
  length age_bucket $8;
  if age_months <= 12 then age_bucket = '0-12';
  else if age_months <= 24 then age_bucket = '13-24';
  else if age_months <= 36 then age_bucket = '25-36';
  else age_bucket = '37+';
run;

proc sql;
  create table result as
  select product, age_bucket, count(*) as loans
  from aged
  group by product, age_bucket
  order by product, age_bucket;
quit;

proc export data=result outfile="&path/out/p06_&size._&copy..csv"
            dbms=csv replace;
run;
