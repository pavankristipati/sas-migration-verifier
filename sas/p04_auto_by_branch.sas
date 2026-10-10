/* p04_auto_by_branch.sas
   Auto loans only: number of loans and total amount originated, by branch.
   Branch names are cleaned to proper case (Columbus, not COLUMBUS). */

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

data auto;
  set loans;
  where product = 'AUTO';
  length branch_name $12;
  branch_name = propcase(branch);
run;

proc sql;
  create table result as
  select branch_name,
         count(*)                          as loans,
         round(sum(original_amount), 0.01) as total_original format=15.2
  from auto
  group by branch_name
  order by branch_name;
quit;

proc export data=result outfile="&path/out/p04_&size._&copy..csv"
            dbms=csv replace;
run;
