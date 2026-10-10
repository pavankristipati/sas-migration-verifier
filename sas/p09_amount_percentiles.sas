/* p09_amount_percentiles.sas
   Median and 90th percentile of the amount originated, by product. */

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

proc means data=loans noprint nway;
  class product;
  var original_amount;
  output out=stats n=n median=median_amount p90=p90_amount;
run;

data result;
  set stats;
  keep product n median_amount p90_amount;
  format median_amount p90_amount 15.2;
run;

proc export data=result outfile="&path/out/p09_&size._&copy..csv"
            dbms=csv replace;
run;
