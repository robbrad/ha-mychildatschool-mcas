# MyChildAtSchool (MCAS) for Home Assistant

Home Assistant integration for the [MyChildAtSchool](https://www.mychildatschool.com)
parent portal (Bromcom MCAS), exposing your child's attendance, behaviour,
detentions and dinner balance as sensors.

## Sensors

| Sensor | Description |
| --- | --- |
| `Attendance today` | `Present` / `Not present` / `No data`, with each period's mark as attributes |
| `Attendance this week` | Percentage of recorded school days present in the last 7 days |
| `Behaviour events` | Count of behaviour events in the last 7 days, with the events (including the behaviour level, e.g. "Lesson Mark 1: Above Expected Attitude and Behaviour") as attributes |
| `Behaviour points` | Behaviour points for the academic year, with positive/negative splits, all-time totals, a per-subject breakdown and the most recent events |
| `Detentions` | Outstanding detentions |
| `Dinner balance` | Dinner money credit balance (GBP) |

## Installation

Add this repository as a custom repository in HACS, install, restart Home
Assistant, then add **MyChildAtSchool (MCAS)** from
*Settings → Devices & Services* and sign in with your parent portal account.

## How it works

MCAS is an ASP.NET WebForms site, but its pages talk to a real `api/v1` REST
backend through a single generic proxy web service. This integration logs in with
the normal parent credentials and then calls that backend directly, which is far
more robust than scraping the rendered pages.

Attendance is served one day at a time, so past school days are cached for the
life of the config entry and only today and yesterday are re-fetched. That keeps
the load on the school's portal to a few requests per poll. Behaviour events are
only available as an HTML fragment and are parsed with BeautifulSoup.

## Notes

- One MCAS login covers one pupil; the pupil's student ID is used as the unique ID.
- If the school hasn't enabled a module for parents, the related sensor will read
  zero or `No data` rather than erroring.

## Disclaimer

Not affiliated with or endorsed by Bromcom. Uses the same endpoints as the parent
portal, with your own credentials.
