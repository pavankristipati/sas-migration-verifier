/* p01_delinquency_by_product.sas
   For the last month-end (Sep 30, 2026), by product:
     loans              number of loans
     delinquent_loans   loans 30 or more days past due
     low_balance_loans  loans with balance under $1,000
     total_balance      sum of balances
   Change COPY to hidden to build the hidden answer key. */

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
  create table last_month as
  select p.loan_id, l.product, p.balance, p.days_past_due
  from payments as p inner join loans as l
    on p.loan_id = l.loan_id
  where p.month_end = '30SEP2026'd;
quit;

data flagged;
  set last_month;
  delinquent  = (days_past_due >= 30);
  low_balance = (balance < 1000);
run;

proc sql;
  create table result as
  select product,
         count(*)                   as loans,
         sum(delinquent)            as delinquent_loans,
         sum(low_balance)           as low_balance_loans,
         round(sum(balance), 0.01)  as total_balance format=15.2
  from flagged
  group by product
  order by product;
quit;

proc export data=result outfile="&path/out/p01_&size._&copy..csv"
            dbms=csv replace;
run;

proc print data=result noobs; run;
