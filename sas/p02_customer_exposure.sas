/* p02_customer_exposure.sas
   For each customer, as of Sep 30, 2026: number of loans and total balance owed.
   Built with a DATA step that walks rows in customer order (BY-group processing). */

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

proc sql;
  create table sep as
  select l.customer_id, p.loan_id, p.balance
  from payments as p inner join loans as l
    on p.loan_id = l.loan_id
  where p.month_end = '30SEP2026'd
  order by l.customer_id, p.loan_id;
quit;

data result;
  set sep;
  by customer_id;
  if first.customer_id then do;
    loans = 0;
    total_balance = 0;
  end;
  loans + 1;
  total_balance + balance;
  if last.customer_id then output;
  keep customer_id loans total_balance;
  format total_balance 15.2;
run;

proc export data=result outfile="&path/out/p02_&size._&copy..csv"
            dbms=csv replace;
run;
