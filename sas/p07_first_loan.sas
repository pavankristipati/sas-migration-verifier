/* p07_first_loan.sas
   Each customer's first loan: the one with the earliest origination date.
   When two loans share that date, the one listed first in the file wins. */

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

proc sort data=loans out=s;
  by customer_id origination_date;
run;

data result;
  set s;
  by customer_id;
  if first.customer_id;
  keep customer_id loan_id origination_date product;
run;

proc export data=result outfile="&path/out/p07_&size._&copy..csv"
            dbms=csv replace;
run;
