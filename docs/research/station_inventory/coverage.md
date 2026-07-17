# Delhi Station Coverage Report

> Generated 2026-07-17 by `scripts/coverage_report.py`.
> Coverage probed against the **OpenAQ S3 archive** — the only source whose
> claimed coverage matches what it will actually return.

## Summary

- **96** locations within 25 km of Delhi centre
- **96** have data in the archive
- **48** have a gap in their year range

## Stations per year

| Year | Stations |                                                                    |
| ---- | -------: | ------------------------------------------------------------------ |
| 2015 |        7 | ███████                                                            |
| 2016 |       11 | ███████████                                                        |
| 2017 |       10 | ██████████                                                         |
| 2018 |       66 | ██████████████████████████████████████████████████████████████████ |
| 2019 |       46 | ██████████████████████████████████████████████                     |
| 2020 |       51 | ███████████████████████████████████████████████████                |
| 2021 |       51 | ███████████████████████████████████████████████████                |
| 2022 |       50 | ██████████████████████████████████████████████████                 |
| 2023 |        1 | █                                                                  |
| 2024 |        2 | ██                                                                 |
| 2025 |       55 | ███████████████████████████████████████████████████████            |
| 2026 |       63 | ███████████████████████████████████████████████████████████████    |

**The 2023-2024 gap is real.** No trend may be drawn across it; see
`docs/research/scientific-limitations.md` §3.1.

## Pollutant availability

| Pollutant        | Stations |
| ---------------- | -------: |
| pm25             |       94 |
| no2              |       88 |
| o3               |       85 |
| co               |       84 |
| pm10             |       83 |
| so2              |       72 |
| no               |       56 |
| nox              |       56 |
| relativehumidity |       52 |
| temperature      |       52 |
| wind_direction   |       46 |
| wind_speed       |       46 |
| pm1              |        6 |
| um003            |        6 |

Counts are stations that have _ever_ carried a sensor for the pollutant,
across vintages — not stations reporting it today.

## Providers

| Provider          | Stations |
| ----------------- | -------: |
| CPCB              |       57 |
| caaqm             |       23 |
| N/A               |        8 |
| AirGradient       |        6 |
| StateAir NewDelhi |        1 |
| AirNow            |        1 |

Providers are not interchangeable: `CPCB` are reference-grade regulatory
monitors, `AirGradient` are low-cost sensors with different uncertainty.
Mixing them into one mean without weighting is unsound.

## Stations

| Location                               | Provider          | Years          | Gap? | Pollutants                                            |
| -------------------------------------- | ----------------- | -------------- | ---- | ----------------------------------------------------- |
| New Delhi                              | AirNow            | 2016-2026 (11) |      | pm25                                                  |
| Aya Nagar, New Delhi - IMD             | CPCB              | 2018-2026 (7)  | yes  | co, no, no2, nox, o3, pm10                            |
| Sirifort, Delhi - CPCB                 | CPCB              | 2018-2026 (7)  | yes  | co, no, no2, nox, o3, pm10                            |
| Sector - 125, Noida, UP - UPPCB        | CPCB              | 2018-2026 (7)  | yes  | co, no, no2, nox, o3, pm10                            |
| North Campus, DU, Delhi - IMD          | CPCB              | 2018-2026 (7)  | yes  | co, no, no2, nox, o3, pm10                            |
| Sector - 62, Noida, UP - IMD           | CPCB              | 2018-2026 (7)  | yes  | co, no, no2, nox, o3, pm10                            |
| NSIT Dwarka, Delhi - CPCB              | CPCB              | 2018-2026 (7)  | yes  | co, no, no2, nox, o3, pm10                            |
| DTU, New Delhi - CPCB                  | CPCB              | 2018-2026 (7)  | yes  | co, no, no2, nox, o3, pm10                            |
| CRRI Mathura Road, New Delhi - IMD     | CPCB              | 2018-2026 (7)  | yes  | co, no, no2, nox, o3, pm10                            |
| Shadipur, Delhi - CPCB                 | CPCB              | 2018-2026 (7)  | yes  | co, no, no2, nox, o3, pm10                            |
| Lodhi Road, New Delhi - IMD            | CPCB              | 2018-2026 (7)  | yes  | co, no, no2, nox, o3, pm10                            |
| IGI Airport (T3), Delhi - IMD          | CPCB              | 2018-2026 (7)  | yes  | co, no, no2, nox, o3, pm10                            |
| Vasundhara, Ghaziabad - UPPCB          | CPCB              | 2018-2026 (7)  | yes  | co, no, no2, nox, o3, pm10                            |
| Pusa, Delhi - DPCC                     | CPCB              | 2018-2026 (7)  | yes  | co, no, no2, nox, o3, pm10                            |
| Mandir Marg, New Delhi - DPCC          | CPCB              | 2018-2026 (7)  | yes  | co, no, no2, nox, o3, pm10                            |
| IHBAS, Dilshad Garden,New Delhi - CPCB | CPCB              | 2018-2026 (7)  | yes  | co, no, no2, nox, o3, pm10                            |
| Major Dhyan Chand National Stadium, De | CPCB              | 2018-2026 (7)  | yes  | co, no, no2, nox, o3, pm10                            |
| Dwarka-Sector 8, Delhi - DPCC          | CPCB              | 2018-2026 (7)  | yes  | co, no, no2, nox, o3, pm10                            |
| Alipur, Delhi - DPCC                   | CPCB              | 2018-2026 (7)  | yes  | co, no, no2, nox, o3, pm10                            |
| Dr. Karni Singh Shooting Range, Delhi  | CPCB              | 2018-2026 (7)  | yes  | co, no, no2, nox, o3, pm10                            |
| Vivek Vihar, Delhi - DPCC              | CPCB              | 2018-2026 (7)  | yes  | co, no, no2, nox, o3, pm10                            |
| Jawaharlal Nehru Stadium, Delhi - DPCC | CPCB              | 2018-2026 (7)  | yes  | co, no, no2, nox, o3, pm10                            |
| Patparganj, Delhi - DPCC               | CPCB              | 2018-2026 (7)  | yes  | co, no, no2, nox, o3, pm10                            |
| Jahangirpuri, Delhi - DPCC             | CPCB              | 2018-2026 (7)  | yes  | co, no, no2, nox, o3, pm10                            |
| Okhla Phase-2, Delhi - DPCC            | CPCB              | 2018-2026 (7)  | yes  | co, no, no2, nox, o3, pm10                            |
| Nehru Nagar, Delhi - DPCC              | CPCB              | 2018-2026 (7)  | yes  | co, no, no2, nox, o3, pm10                            |
| Bawana, Delhi - DPCC                   | CPCB              | 2018-2026 (7)  | yes  | co, no, no2, nox, o3, pm10                            |
| Sonia Vihar, Delhi - DPCC              | CPCB              | 2018-2026 (7)  | yes  | co, no, no2, nox, o3, pm10                            |
| Wazirpur, Delhi - DPCC                 | CPCB              | 2018-2026 (7)  | yes  | co, no, no2, nox, o3, pm10                            |
| Ashok Vihar, Delhi - DPCC              | CPCB              | 2018-2026 (7)  | yes  | co, no, no2, nox, o3, pm10                            |
| Sri Aurobindo Marg, Delhi - DPCC       | CPCB              | 2018-2026 (7)  | yes  | co, no, no2, nox, o3, pm10                            |
| Mundka, Delhi - DPCC                   | CPCB              | 2018-2026 (7)  | yes  | co, no, no2, nox, o3, pm10                            |
| Rohini, Delhi - DPCC                   | CPCB              | 2018-2026 (7)  | yes  | co, no, no2, nox, o3, pm10                            |
| NISE Gwal Pahari, Gurugram - IMD       | CPCB              | 2018-2026 (7)  | yes  | co, no, no2, nox, o3, pm10                            |
| R K Puram, Delhi - DPCC                | CPCB              | 2015-2026 (6)  | yes  | co, no, no2, nox, o3, pm10                            |
| Punjabi Bagh, Delhi - DPCC             | CPCB              | 2015-2026 (6)  | yes  | co, no, no2, nox, o3, pm10                            |
| Anand Vihar, New Delhi - DPCC          | CPCB              | 2015-2026 (6)  | yes  | co, no, no2, nox, o3, pm10                            |
| Burari Crossing, New Delhi - IMD       | CPCB              | 2018-2026 (6)  | yes  | co, no, no2, nox, o3, pm10                            |
| Indirapuram, Ghaziabad - UPPCB         | CPCB              | 2019-2026 (6)  | yes  | co, no, no2, nox, o3, pm10                            |
| Sector-1, Noida - UPPCB                | CPCB              | 2019-2026 (6)  | yes  | co, no, no2, nox, o3, pm10                            |
| Knowledge Park - V, Greater Noida - UP | CPCB              | 2019-2026 (6)  | yes  | co, no, no2, nox, o3, pm10                            |
| Sector-116, Noida - UPPCB              | CPCB              | 2019-2026 (6)  | yes  | co, no, no2, nox, o3, pm10                            |
| Loni, Ghaziabad - UPPCB                | CPCB              | 2019-2026 (6)  | yes  | co, no, no2, nox, o3, pm10                            |
| ITO, New Delhi - CPCB                  | CPCB              | 2018-2026 (5)  | yes  | co, no, no2, nox, o3, pm10                            |
| Sector- 16A, Faridabad - HSPCB         | caaqm             | 2018-2022 (5)  |      | co, no2, o3, pm10, pm25, so2                          |
| Punjabi Bagh, Delhi - DPCC             | caaqm             | 2018-2022 (5)  |      | co, no2, o3, pm10, pm25, so2                          |
| R K Puram, Delhi - DPCC                | caaqm             | 2018-2022 (5)  |      | co, no2, o3, pm10, pm25, so2                          |
| Sector 30, Faridabad - HSPCB           | CPCB              | 2020-2026 (5)  | yes  | co, no, no2, nox, o3, pm10                            |
| Teri Gram, Gurugram - HSPCB            | CPCB              | 2020-2026 (5)  | yes  | co, no, no2, nox, o3, pm10                            |
| Chandni Chowk, Delhi - IITM            | CPCB              | 2020-2026 (5)  | yes  | co, no, no2, nox, o3, pm10                            |
| Delhi Technological University, Delhi  | CPCB              | 2015-2018 (4)  |      | no2, o3, pm25                                         |
| Mandir Marg, Delhi - DPCC              | CPCB              | 2015-2018 (4)  |      | co, no2, o3, pm10, pm25, so2                          |
| Anand Vihar, Delhi - DPCC              | caaqm             | 2018-2021 (4)  |      | co, no2, o3, pm10, pm25, so2                          |
| Lodhi Road, Delhi - IITM               | CPCB              | 2020-2025 (4)  | yes  | co, no2, o3, pm10, pm25, relativehumidity             |
| Income Tax Office, Delhi - CPCB        | CPCB              | 2016-2018 (3)  |      | co, no2, o3, pm10, pm25                               |
| IHBAS, Delhi - CPCB                    | CPCB              | 2016-2018 (3)  |      | co, no2, pm25, so2                                    |
| Shadipur, Delhi - CPCB                 | CPCB              | 2016-2018 (3)  |      | co, no2, o3, pm25, so2                                |
| Sector16A, Faridabad - HSPCB           | CPCB              | 2016-2018 (3)  |      | co, no2, o3, pm10, pm25, so2                          |
| Anand Vihar, Delhi - DPCC              | caaqm             | 2018-2022 (3)  | yes  | co, no2, o3, pm10, pm25, so2                          |
| East Arjun Nagar, Delhi - CPCB         | caaqm             | 2018-2020 (3)  |      | no2, o3, so2                                          |
| East Arjun Nagar, Delhi - CPCB         | caaqm             | 2020-2022 (3)  |      | no2, o3, so2                                          |
| ITO, Delhi - CPCB                      | caaqm             | 2020-2022 (3)  |      | co, no2, o3, pm10, pm25, so2                          |
| GK1 (Oberoi Terrace)                   | AirGradient       | 2024-2026 (3)  |      | pm1, pm10, pm25, relativehumidity, temperature, um003 |
| Pusa, Delhi - IMD                      | CPCB              | 2025-2026 (2)  |      | co, no, no2, nox, o3, pm10                            |
| Santushti Apartments, Vasant Kunj      | AirGradient       | 2025-2026 (2)  |      | pm1, pm25, relativehumidity, temperature, um003       |
| Sector 1, Noida extension              | AirGradient       | 2025-2026 (2)  |      | pm1, pm25, relativehumidity, temperature, um003       |
| Sector - 5, Vasundhara, Ghaziabad, Utt | AirGradient       | 2025-2026 (2)  |      | pm1, pm25, relativehumidity, temperature, um003       |
| Anand Lok                              | AirGradient       | 2025-2026 (2)  |      | pm1, pm25, relativehumidity, temperature, um003       |
| IIT Delhi, Delhi - IITM                | N/A               | 2025-2026 (2)  |      | co, no, no2, nox, o3, pm10                            |
| IGI Airport                            | CPCB              | 2015-2015 (1)  |      | co, no2, o3, pm10, pm25                               |
| Civil Lines                            | CPCB              | 2015-2015 (1)  |      | co, no2, pm10, pm25                                   |
| US Diplomatic Post: New Delhi          | StateAir NewDelhi | 2016-2016 (1)  |      | pm25                                                  |
| Punjabi Bagh, Delhi - DPCC             | caaqm             | 2018-2018 (1)  |      | co, no2, o3, pm10, pm25, so2                          |
| Pusa, New Delhi - IMD                  | caaqm             | 2018-2018 (1)  |      | co, no2, o3, pm10, pm25                               |
| R K Puram, New Delhi - DPCC            | caaqm             | 2018-2018 (1)  |      | co, no2, o3, pm10, pm25, so2                          |
| Mandir Marg, New Delhi - DPCC          | caaqm             | 2018-2018 (1)  |      | co, no2, o3, pm10, pm25, so2                          |
| Patparganj, Delhi - DPCC               | caaqm             | 2018-2018 (1)  |      | no2, o3, pm10, pm25, so2                              |
| Rohini, Delhi - DPCC                   | caaqm             | 2018-2018 (1)  |      | co, no2, o3, pm10, pm25, so2                          |
| Dr. Karni Singh Shooting Range, Delhi  | caaqm             | 2018-2018 (1)  |      | co, no2, o3, pm10, pm25, so2                          |
| Vivek Vihar, Delhi - DPCC              | caaqm             | 2018-2018 (1)  |      | co, no2, o3, pm10, pm25, so2                          |
| Jawaharlal Nehru Stadium, Delhi - DPCC | caaqm             | 2018-2018 (1)  |      | co, no2, o3, pm10, pm25, so2                          |
| Major Dhyan Chand National Stadium, De | caaqm             | 2018-2018 (1)  |      | co, no2, o3, pm10, pm25, so2                          |
| Sonia Vihar, Delhi - DPCC              | caaqm             | 2018-2018 (1)  |      | co, no2, o3, pm10, pm25, so2                          |
| Jahangirpuri, Delhi - DPCC             | caaqm             | 2018-2018 (1)  |      | co, no2, o3, pm10, pm25, so2                          |
| Ashok Vihar, Delhi - DPCC              | caaqm             | 2018-2018 (1)  |      | co, no2, o3, pm10, pm25, so2                          |
| Okhla Phase-2, Delhi - DPCC            | caaqm             | 2018-2018 (1)  |      | co, no2, o3, pm10, pm25, so2                          |
| Nehru Nagar, Delhi - DPCC              | caaqm             | 2018-2018 (1)  |      | co, no2, o3, pm10, pm25, so2                          |
| New Moti Bagh, Delhi - MHUA            | CPCB              | 2026-2026 (1)  |      | co, no, no2, nox, pm25, relativehumidity              |
| Air Check                              | AirGradient       | 2026-2026 (1)  |      | pm1, pm25, relativehumidity, temperature, um003       |
| Talkatora Garden, Delhi - DPCC         | N/A               | 2026-2026 (1)  |      | co, no, no2, nox, o3, pm10                            |
| JNU, Delhi - DPCC                      | N/A               | 2026-2026 (1)  |      | co, no, no2, nox, o3, pm10                            |
| Commonwealth Sports Complex, Delhi - D | N/A               | 2026-2026 (1)  |      | co, no, no2, nox, o3, pm10                            |
| IGNOU_Maidan Garhi, Delhi - DPCC       | N/A               | 2026-2026 (1)  |      | co, no, no2, nox, o3, pm10                            |
| Cantonment Area, Delhi - DPCC          | N/A               | 2026-2026 (1)  |      | co, no, no2, nox, o3, pm10                            |
| Prashant Garden, Khora - UPPCB         | N/A               | 2026-2026 (1)  |      | co, no, no2, nox, o3, pm10                            |
| Ved Vihar-Loni, Ghaziabad - UPPCB      | N/A               | 2026-2026 (1)  |      | co, no, no2, nox, o3, pm10                            |
