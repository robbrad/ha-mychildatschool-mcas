# Changelog

All notable changes to this project are documented here.
This project adheres to [Semantic Versioning](https://semver.org/).

## 0.1.0

Initial release.

- Attendance (today and a rolling week percentage), from the JSON `tableRawData`
  endpoint rather than the rendered table.
- Behaviour points for the academic year, with positive/negative splits, all-time
  totals and a per-subject breakdown, plus recent behaviour events including the
  level wording.
- Detentions.
- Timetable: lessons today and the next lesson, parsed from the portal's weekly
  grid (MCAS publishes no API for it).
- School day type - School day / Weekend / Holiday / Staff day - decoded from the
  school's own calendar, plus the next school day.
- Reports.
- Sensors are only created for modules the school has enabled, so a disabled
  module produces no permanently-zero entity and costs no API call.
