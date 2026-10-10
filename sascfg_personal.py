"""
sascfg_personal.py: tells SASPy how to reach SAS OnDemand for Academics.

No secrets live in this file. The login comes from two environment variables,
ODA_USER and ODA_PW, which you load from macOS Keychain into the Terminal
session before running anything. Safe to commit to GitHub.

Your SAS Studio address showed odaws02-usw2-2, which is US Home Region 2.
"""
import os

SAS_config_names = ["oda"]

oda = {
    "java": os.path.join(os.environ.get("JAVA_HOME", "/usr"), "bin", "java"),
    "iomhost": ["odaws01-usw2-2.oda.sas.com", "odaws02-usw2-2.oda.sas.com"],
    "iomport": 8591,
    "encoding": "utf-8",
    "omruser": os.environ.get("ODA_USER"),
    "omrpw": os.environ.get("ODA_PW"),
}
