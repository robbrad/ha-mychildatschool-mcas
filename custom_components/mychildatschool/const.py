"""Constants for the MyChildAtSchool (MCAS) integration."""
from datetime import timedelta

DOMAIN = "mychildatschool"

BASE_URL = "https://www.mychildatschool.com"
LOGIN_PATH = "/MCAS/MCSParentLogin"
DASHBOARD_MARKER = "MCSDashboard"
# Generic server-side proxy onto the api/v1 REST backend. Every data call goes
# through this: {"url": "api/v1/...", ...} -> {"d": "<json string or html>"}.
PROXY_PATH = "/MCAS/WebServices/MCSAPIRequestProxy.asmx/CreateGetRequest"

# api/v1 routes. The full route map is a public file served by the portal at
# /Scripts/Blankon/Custom/apiEndPoints.js - consult it before inventing a path.
EP_USER_DETAILS = "api/v1/mcas/user/details"
EP_STUDENT_YEARS = "api/v1/mcas/homework/studentYears/{sid}"
# tableRawData is the JSON sibling of .../table/ (which returns an HTML fragment).
EP_ATTENDANCE = "api/v1/attendance/mcas/tableRawData/{sid}/{y}/{m}/{d}/-1"
EP_BEHAVIOUR = "api/v1/eventRecords/mcas/eventstable/{sid}/{yid}/{y}/{m}/{d}/-1"
EP_DETENTIONS = "api/v1/detentions/mcas/{sid}"
EP_DINNER = "api/v1/mcas/dashboard/GetDinnerBalanceWidgetData/{sid}"

CONF_EMAIL = "email"
CONF_PASSWORD = "password"

DEFAULT_SCAN_INTERVAL = timedelta(minutes=30)
# How many calendar days back to consider "this week" when summarising.
WEEK_LOOKBACK_DAYS = 7
# Marks that count as the pupil being in school.
PRESENT_MARK_SIGNS = {"P", "L"}
