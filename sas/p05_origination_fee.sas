/* p05_origination_fee.sas
   For every loan: the amount rounded to cents and a 1.25% origination fee
   rounded to cents. */

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

data result;
  set loans;
  amount_cents    = round(original_amount, 0.01);
  origination_fee = round(original_amount * 0.0125, 0.01);
  keep loan_id original_amount amount_cents origination_fee;
  format original_amount 15.3 amount_cents origination_fee 15.2;
run;

proc sort data=result;
  by loan_id;
run;

proc export data=result outfile="&path/out/p05_&size._&copy..csv"
            dbms=csv replace;
run;
