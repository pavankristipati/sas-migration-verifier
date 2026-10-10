/* p03_delinquency_streak.sas
   For each loan, the longest run of consecutive months at 30+ days past due.
   Lists loans whose longest run is 3 months or more. */

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

data streaks;
  set p;
  by loan_id;
  retain streak max_streak;
  if first.loan_id then do;
    streak = 0;
    max_streak = 0;
  end;
  if days_past_due >= 30 then streak + 1;
  else streak = 0;
  max_streak = max(max_streak, streak);
  if last.loan_id then output;
  keep loan_id max_streak;
run;

data result;
  set streaks;
  where max_streak >= 3;
run;

proc export data=result outfile="&path/out/p03_&size._&copy..csv"
            dbms=csv replace;
run;
