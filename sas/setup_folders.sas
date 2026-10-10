/* setup_folders.sas: creates the lab folders in your SAS OnDemand home.
   Run once. DLCREATEDIR tells SAS to create a folder when a LIBNAME
   points at one that does not exist yet. */
options dlcreatedir;
%let path = /home/&sysuserid/lab;

libname f1 "&path";
libname f2 "&path/data";
libname f3 "&path/data/1k";
libname f4 "&path/data/1k/practice";
libname f5 "&path/data/1k/hidden";
libname f6 "&path/out";
libname _all_ clear;

%put NOTE: Lab folders are ready under &path;
