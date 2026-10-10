/* p08_monthly_paydown.sas
   Month-over-month change in balance for each loan, averaged by product. */

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

proc sort data=payments out=p;
  by loan_id month_end;
run;

data chg;
  set p;
  by loan_id;
  prev_balance = lag(balance);
  if first.loan_id then prev_balance = .;
  change = balance - prev_balance;
run;

proc sql;
  create table result as
  select l.product,
         count(c.change)              as months_with_change,
         round(mean(c.change), 0.01)  as avg_monthly_change format=12.2
  from chg as c inner join loans as l
    on c.loan_id = l.loan_id
  group by l.product
  order by l.product;
quit;

proc export data=result outfile="&path/out/p08_&size._&copy..csv"
            dbms=csv replace;
run;
