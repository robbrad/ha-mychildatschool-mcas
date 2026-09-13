"""Tests for the MCAS client: WebForms login, the .asmx proxy, and the parsers."""

import json

import pytest
import requests
import responses

from custom_components.mychildatschool.api import (
    MCASAuthError,
    MCASClient,
    _parse_day_header,
)
from custom_components.mychildatschool.const import BASE_URL, LOGIN_PATH, PROXY_PATH

# Fabricated - must match the values used in conftest.py's fixtures.
STUDENT_ID = 99999
SCHOOL_ID = 88888
YEAR_ID = 40000

LOGIN_URL = f"{BASE_URL}{LOGIN_PATH}"
PROXY_URL = f"{BASE_URL}{PROXY_PATH}"
DASHBOARD_URL = f"{BASE_URL}/MCAS/MCSDashboardPage"


@pytest.fixture
def client():
    return MCASClient(requests.Session(), "parent@example.com", "hunter2")


def _mock_login(rsps, login_html, dashboard_html):
    rsps.add(responses.GET, LOGIN_URL, body=login_html, status=200)
    rsps.add(
        responses.POST,
        LOGIN_URL,
        body=dashboard_html,
        status=200,
        headers={"Location": DASHBOARD_URL},
    )


@responses.activate
def test_login_posts_hidden_fields_and_reads_context(
    client, login_html, dashboard_html
):
    """The WebForms hidden fields must be echoed back or the post is rejected."""
    responses.add(responses.GET, LOGIN_URL, body=login_html, status=200)
    # A successful login 302s to the dashboard; landing there is the only success
    # signal MCAS gives, so the redirect has to be followed.
    responses.add(
        responses.POST,
        LOGIN_URL,
        status=302,
        headers={"Location": DASHBOARD_URL},
        body="",
    )
    responses.add(responses.GET, DASHBOARD_URL, body=dashboard_html, status=200)
    client.login()

    posted = next(c for c in responses.calls if c.request.method == "POST")
    assert "__VIEWSTATE=abc123" in posted.request.body
    assert "__EVENTVALIDATION=xyz789" in posted.request.body
    assert "EmailTextBox=parent%40example.com" in posted.request.body

    assert client.student_id == STUDENT_ID
    assert client.school_id == SCHOOL_ID
    assert client.school_name == "Example High School"
    # The header renders "Surname, Forename"; entities should read naturally.
    assert client.student_name == "Alex Smith"


@responses.activate
def test_login_failure_raises_auth_error(client, login_html):
    """MCAS re-renders the login page rather than returning an error status."""
    responses.add(responses.GET, LOGIN_URL, body=login_html, status=200)
    responses.add(responses.POST, LOGIN_URL, body=login_html, status=200)
    with pytest.raises(MCASAuthError):
        client.login()


@pytest.mark.parametrize(
    ("payload", "expected"),
    [
        (json.dumps({"Table": [{"a": 1}]}), {"Table": [{"a": 1}]}),
        ("<table><tr><td>x</td></tr></table>", "<table><tr><td>x</td></tr></table>"),
        ("", None),
        (None, None),
        # A bad path comes back as HTTP 200 with this string, not a 404 status.
        ("Error 404 - Requested API call reference Not Found.", None),
    ],
)
@responses.activate
def test_proxy_decodes_double_encoded_payloads(client, payload, expected):
    responses.add(responses.POST, PROXY_URL, json={"d": payload}, status=200)
    assert client._get("api/v1/anything") == expected


@responses.activate
def test_behaviour_year_computes_points_and_maps_subjects(client):
    """Summing Adjustment reproduces the total the portal shows."""
    client.student_id, client.year_id = STUDENT_ID, YEAR_ID
    responses.add(
        responses.POST,
        PROXY_URL,
        json={
            "d": json.dumps(
                {
                    "Table": [
                        {
                            "EventDate": "2026-09-11T09:00:00",
                            "EventType": "Positive",
                            "Adjustment": 2,
                            "SubjectID": 1,
                            "EventRecordID": 10,
                        },
                        {
                            "EventDate": "2026-09-10T09:00:00",
                            "EventType": "Neutral",
                            "Adjustment": 0,
                            "SubjectID": 2,
                            "EventRecordID": 11,
                        },
                        {
                            "EventDate": "2026-09-09T09:00:00",
                            "EventType": "Negative",
                            "Adjustment": -1,
                            "SubjectID": 1,
                            "EventRecordID": 12,
                        },
                    ],
                    "Table1": [
                        {"Day": "2026-09-11T00:00:00", "DayStatusCode": "-"},
                        {"Day": "2026-09-12T00:00:00", "DayStatusCode": "*"},
                        {"Day": "2026-09-14T00:00:00", "DayStatusCode": "#"},
                        {"Day": "2026-09-15T00:00:00", "DayStatusCode": "$"},
                    ],
                    "Table2": [{"YearName": "2026/2027"}],
                    "Table3": [
                        {"SubjectID": 1, "SubjectName": "Music"},
                        {"SubjectID": 2, "SubjectName": "Maths"},
                    ],
                    "Table4": {},
                }
            )
        },
        status=200,
    )
    result = client.behaviour_year()
    assert result["year_name"] == "2026/2027"
    assert result["points"]["positive"] == 2
    assert result["points"]["negative"] == 1
    assert result["points"]["total"] == 1
    # Newest first, with SubjectID resolved to a name.
    assert result["events"][0]["subject"] == "Music"
    assert result["events"][0]["date"].startswith("2026-09-11")
    assert result["calendar"] == {
        "2026-09-11": "School day",
        "2026-09-12": "Weekend",
        "2026-09-14": "Holiday",
        "2026-09-15": "Staff day",
    }


@responses.activate
def test_all_time_totals_tolerate_na(client):
    """Schools can hide a figure, in which case the API returns the string "N/A"."""
    client.student_id, client.year_id = STUDENT_ID, YEAR_ID
    responses.add(
        responses.POST,
        PROXY_URL,
        json={
            "d": json.dumps(
                {
                    "Table": [],
                    "Table3": [],
                    "Table4": [
                        {
                            "ShowTotalPointsAllTime": "12",
                            "PositivePointsAllTime": "12",
                            "NegativePointsAllTime": "N/A",
                        }
                    ],
                }
            )
        },
        status=200,
    )
    points = client.behaviour_year()["points"]
    assert points["all_time_total"] == 12
    assert points["all_time_negative"] is None


def test_parse_behaviour_reads_the_html_table(client, behaviour_html):
    events = client._parse_behaviour(behaviour_html)
    assert len(events) == 2
    assert events[0]["Subject"] == "Music"
    # The level wording exists only in the HTML view, not the JSON one.
    assert "Lesson Mark 1" in events[0]["Event"]


@pytest.mark.parametrize("value", [None, "", "<table></table>", 12345])
def test_parse_behaviour_handles_junk(client, value):
    assert client._parse_behaviour(value) == []


@responses.activate
def test_timetable_prefers_title_attributes(client, timetable_html):
    """Visible cell text is ellipsised; `title` holds the real value."""
    responses.add(
        responses.GET,
        f"{BASE_URL}/MCAS/MCSTimetable.aspx",
        body=timetable_html,
        status=200,
    )
    lessons = client.timetable()
    assert len(lessons) == 4
    tutor = [x for x in lessons if x["period"] == "Tutor"]
    assert tutor[0]["subject"] == "Tutor Period"
    assert tutor[0]["teacher"] == "Ms Example"
    assert tutor[0]["day"] == "Monday"
    assert {x["subject"] for x in lessons} == {"Tutor Period", "Rel. Stud.", "Drama"}


@responses.activate
def test_modules_parses_string_booleans(client):
    """Flags come back as the strings "True"/"False" with inconsistent casing."""
    responses.add(
        responses.POST,
        PROXY_URL,
        json={
            "d": json.dumps(
                {
                    "Table": [
                        {"KeyName": "MCASAttendanceModuleEnabled", "KeyValue": "True"},
                        {"KeyName": "MCASBehaviourModuleEnabled", "KeyValue": "true"},
                        {
                            "KeyName": "MCASDinnerMoneyModule_EnableDinnerMoneyModule",
                            "KeyValue": "False",
                        },
                        {"KeyName": "MCASClubsModuleEnabled", "KeyValue": "false"},
                    ]
                }
            )
        },
        status=200,
    )
    modules = client.modules()
    assert modules["attendance"] is True
    assert modules["behaviour"] is True
    assert modules["dinner"] is False
    assert modules["clubs"] is False
    # A flag the school never sets should not be reported as enabled.
    assert modules["trips"] is False


@responses.activate
@pytest.mark.parametrize(
    ("html", "expected"),
    [
        ("<span>Credit Balance Summary : £ 12.34</span>", 12.34),
        ("<span>£ -5.00</span>", -5.0),
        ("<span>£ 1,234.56</span>", 1234.56),
        ("<span>no balance published</span>", None),
    ],
)
def test_dinner_balance_scrapes_the_widget(client, html, expected):
    client.student_id = STUDENT_ID
    responses.add(responses.POST, PROXY_URL, json={"d": html}, status=200)
    assert client.dinner_balance() == expected


@pytest.mark.parametrize(
    ("header", "day"),
    [
        ("Monday14th Sep", "Monday"),
        ("Friday1st Nov", "Friday"),
        ("nonsense", "nonsense"),
    ],
)
def test_parse_day_header(header, day):
    assert _parse_day_header(header)[0] == day
