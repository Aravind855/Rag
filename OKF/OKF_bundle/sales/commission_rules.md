---
id: nc.sales.commission_rules
title: Commission Rules
type: Metric
description: Authoritative metric defining commission rules for NexaCore Sales operations.
tags:
- sales
- metric
status: stable
stale_after: '2027-08-01T00:00:00Z'
version: '1.0'
owners:
- sales-operations@nexacore.internal
generated:
  by: automated-okf-parser-pipeline
  at: '2026-10-14T00:00:00Z'
verified:
  by: Head of Sales Governance
  at: '2026-10-14T00:00:00Z'
sources:
- id: commission_rules-source
  resource: /Datasource/sales/commission_rules.xlsx
  title: Source Document commission_rules.xlsx
---

# Commission Rules


## Sheet: Commission_Rules

| Plan Code   | Role                         |   Quota INR Cr |   Base Commission % |   Accelerator 1 |   Accelerator 2 |   Accelerator 3 |   Threshold 1 |   Threshold 2 |   Threshold 3 |   Clawback Window Days |
|:------------|:-----------------------------|---------------:|--------------------:|----------------:|----------------:|----------------:|--------------:|--------------:|--------------:|-----------------------:|
| AE-ENT      | Enterprise Account Executive |            8   |                3    |            1.25 |             1.5 |            2    |             1 |          1.2  |          1.5  |                     90 |
| AE-MID      | Mid-Market Account Executive |            5   |                3    |            1.2  |             1.4 |            1.75 |             1 |          1.15 |          1.35 |                     90 |
| AE-SMB      | SMB Account Executive        |            2.5 |                2.5  |            1.15 |             1.3 |            1.5  |             1 |          1.1  |          1.25 |                     60 |
| AM-ENT      | Enterprise Account Manager   |            6   |                2    |            1.15 |             1.3 |            1.5  |             1 |          1.1  |          1.25 |                    120 |
| SE          | Sales Engineer               |            0   |                0.75 |            1    |             1.1 |            1.25 |             1 |          1.2  |          1.5  |                     90 |
| SDR         | Sales Development Rep        |            0   |                0.4  |            1    |             1.1 |            1.2  |             1 |          1.15 |          1.3  |                     60 |

*Total records: 6 row(s)*


## Sheet: Payout_Calculation

| Employee ID   | Role                         | Plan Code   |   FY26 Quota INR Lakh |   FY26 Eligible Bookings INR Lakh |   Attainment % |   Base Rate % |   Accelerator |   Gross Commission INR |   Clawback INR |   Net Commission INR | Status   |
|:--------------|:-----------------------------|:------------|----------------------:|----------------------------------:|---------------:|--------------:|--------------:|-----------------------:|---------------:|---------------------:|:---------|
| NXC-SAL-0101  | Enterprise Account Executive | AE-ENT      |                   800 |                              1040 |           1.3  |         0.03  |          1.5  |                4680000 |         234000 |              4446000 | Adjusted |
| NXC-SAL-0102  | Enterprise Account Executive | AE-ENT      |                   800 |                               720 |           0.9  |         0.03  |          1    |                2160000 |              0 |              2160000 | Paid     |
| NXC-SAL-0103  | Mid-Market Account Executive | AE-MID      |                   500 |                               590 |           1.18 |         0.03  |          1.15 |                2035500 |              0 |              2035500 | Paid     |
| NXC-SAL-0104  | SMB Account Executive        | AE-SMB      |                   250 |                               315 |           1.26 |         0.025 |          1.3  |                1023750 |              0 |              1023750 | Paid     |
| NXC-SAL-0105  | Enterprise Account Manager   | AM-ENT      |                   600 |                               690 |           1.15 |         0.02  |          1.3  |                1794000 |          89700 |              1704300 | Adjusted |
| NXC-SAL-0106  | Sales Development Rep        | SDR         |                     0 |                                 0 |           0    |         0.004 |          1.1  |                      0 |              0 |                    0 | Paid     |

*Total records: 6 row(s)*


## Sheet: Commissionable_Bookings

| Booking ID   | Employee ID   | Account                 | Booking Date   |   Contract Term Months |   ACV INR Lakh |   Discount % |   Commissionable INR Lakh | Booking Status   | Clawback Eligible   | Region        |
|:-------------|:--------------|:------------------------|:---------------|-----------------------:|---------------:|-------------:|--------------------------:|:-----------------|:--------------------|:--------------|
| BK-2026-0001 | NXC-SAL-0102  | Solstice Energy         | 11-03-2026     |                     36 |          46.13 |          0.5 |                      0    | Clawed Back      | Yes                 | South         |
| BK-2026-0002 | NXC-SAL-0103  | Orion Retail Group      | 09-01-2026     |                     24 |          47.82 |          1.4 |                     47.15 | Approved         | No                  | South         |
| BK-2026-0003 | NXC-SAL-0103  | Aster Mobility          | 06-02-2026     |                     24 |          36.9  |         11.6 |                     32.62 | Approved         | No                  | West          |
| BK-2026-0004 | NXC-SAL-0101  | Meridian Foods          | 22-04-2026     |                     24 |         119.1  |         12   |                      0    | Clawed Back      | Yes                 | South         |
| BK-2026-0005 | NXC-SAL-0103  | Orion Retail Group      | 08-04-2026     |                     24 |          20.93 |         17.7 |                     17.23 | Approved         | No                  | West          |
| BK-2026-0006 | NXC-SAL-0103  | Orion Retail Group      | 20-01-2026     |                     24 |          96.78 |          6.8 |                     90.2  | Approved         | No                  | North         |
| BK-2026-0007 | NXC-SAL-0105  | Cedar Finance           | 21-03-2026     |                     12 |           9.39 |          6   |                      8.83 | Approved         | No                  | South         |
| BK-2026-0008 | NXC-SAL-0104  | Meridian Foods          | 05-04-2026     |                     12 |          19.03 |          1   |                     18.84 | Approved         | No                  | South         |
| BK-2026-0009 | NXC-SAL-0104  | Solstice Energy         | 09-04-2026     |                     24 |         109.89 |         18.7 |                      0    | Clawed Back      | Yes                 | North         |
| BK-2026-0010 | NXC-SAL-0105  | Harbor Telecom          | 18-06-2026     |                     24 |          33.91 |          3.3 |                     32.79 | Approved         | No                  | North         |
| BK-2026-0011 | NXC-SAL-0104  | Cedar Finance           | 15-03-2026     |                     36 |          60.84 |         21.3 |                     47.88 | Pending          | No                  | West          |
| BK-2026-0012 | NXC-SAL-0105  | Orion Retail Group      | 11-07-2026     |                     24 |          28.11 |         13   |                      0    | Clawed Back      | Yes                 | International |
| BK-2026-0013 | NXC-SAL-0101  | Aster Mobility          | 10-04-2026     |                     12 |          88.57 |          7.3 |                      0    | Clawed Back      | Yes                 | International |
| BK-2026-0014 | NXC-SAL-0104  | Aster Mobility          | 13-04-2026     |                     12 |          93.84 |          3.4 |                      0    | Clawed Back      | Yes                 | West          |
| BK-2026-0015 | NXC-SAL-0106  | Orion Retail Group      | 06-01-2026     |                     24 |         116.63 |         18.1 |                     95.52 | Approved         | No                  | West          |
| BK-2026-0016 | NXC-SAL-0105  | Northstar Manufacturing | 15-06-2026     |                     24 |          43.7  |         17.9 |                     35.88 | Pending          | No                  | North         |
| BK-2026-0017 | NXC-SAL-0101  | Quanta Digital          | 19-06-2026     |                     36 |         115.66 |          3.2 |                    111.96 | Pending          | No                  | South         |
| BK-2026-0018 | NXC-SAL-0105  | Solstice Energy         | 17-07-2026     |                     24 |          72.68 |         21.2 |                     57.27 | Approved         | No                  | International |
| BK-2026-0019 | NXC-SAL-0102  | Cedar Finance           | 23-02-2026     |                     12 |          86.93 |         12.8 |                     75.8  | Approved         | No                  | South         |
| BK-2026-0020 | NXC-SAL-0102  | Northstar Manufacturing | 11-06-2026     |                     12 |          56.05 |         21.7 |                     43.89 | Approved         | No                  | International |
| BK-2026-0021 | NXC-SAL-0105  | Harbor Telecom          | 26-04-2026     |                     36 |          73.62 |         15.8 |                     61.99 | Approved         | No                  | West          |
| BK-2026-0022 | NXC-SAL-0105  | BluePeak Logistics      | 02-06-2026     |                     24 |          11.24 |         14.4 |                      9.62 | Approved         | No                  | South         |
| BK-2026-0023 | NXC-SAL-0102  | Vertex Health           | 27-03-2026     |                     36 |          22.37 |          8.5 |                     20.47 | Pending          | No                  | West          |
| BK-2026-0024 | NXC-SAL-0105  | Aster Mobility          | 15-04-2026     |                     12 |          16.76 |          8.9 |                      0    | Clawed Back      | Yes                 | South         |
| BK-2026-0025 | NXC-SAL-0105  | Cedar Finance           | 03-06-2026     |                     24 |          22.67 |         11.7 |                     20.02 | Approved         | No                  | West          |
| BK-2026-0026 | NXC-SAL-0103  | Aster Mobility          | 05-06-2026     |                     24 |          88.52 |          7.6 |                      0    | Clawed Back      | Yes                 | South         |
| BK-2026-0027 | NXC-SAL-0106  | Cedar Finance           | 20-07-2026     |                     12 |          63.87 |         12   |                     56.21 | Approved         | No                  | North         |
| BK-2026-0028 | NXC-SAL-0106  | Cedar Finance           | 09-04-2026     |                     12 |          36.04 |         10.2 |                     32.36 | Approved         | No                  | North         |
| BK-2026-0029 | NXC-SAL-0104  | Orion Retail Group      | 14-07-2026     |                     24 |          91.18 |         20.3 |                     72.67 | Pending          | No                  | West          |
| BK-2026-0030 | NXC-SAL-0101  | Orion Retail Group      | 27-04-2026     |                     24 |           8.27 |          0.7 |                      8.21 | Pending          | No                  | International |
| BK-2026-0031 | NXC-SAL-0101  | Harbor Telecom          | 27-07-2026     |                     12 |          20.58 |          9.6 |                     18.6  | Pending          | No                  | West          |
| BK-2026-0032 | NXC-SAL-0104  | Cedar Finance           | 26-07-2026     |                     24 |          57.74 |          3.6 |                     55.66 | Approved         | No                  | International |
| BK-2026-0033 | NXC-SAL-0106  | Harbor Telecom          | 15-02-2026     |                     36 |          12.54 |          5.3 |                     11.88 | Approved         | No                  | International |
| BK-2026-0034 | NXC-SAL-0105  | Orion Retail Group      | 25-03-2026     |                     36 |          97.65 |         21.3 |                     76.85 | Approved         | No                  | North         |
| BK-2026-0035 | NXC-SAL-0102  | Meridian Foods          | 16-07-2026     |                     36 |         111.52 |         19.8 |                     89.44 | Approved         | No                  | North         |
| BK-2026-0036 | NXC-SAL-0101  | Quanta Digital          | 01-07-2026     |                     12 |          95.44 |         11.4 |                     84.56 | Pending          | No                  | North         |
| BK-2026-0037 | NXC-SAL-0101  | BluePeak Logistics      | 27-01-2026     |                     24 |          38.85 |         14   |                     33.41 | Pending          | No                  | West          |
| BK-2026-0038 | NXC-SAL-0105  | Northstar Manufacturing | 04-07-2026     |                     12 |           9.23 |         14.1 |                      7.93 | Pending          | No                  | West          |
| BK-2026-0039 | NXC-SAL-0103  | Solstice Energy         | 22-04-2026     |                     12 |          92.52 |          7.6 |                      0    | Clawed Back      | Yes                 | West          |
| BK-2026-0040 | NXC-SAL-0104  | Solstice Energy         | 12-04-2026     |                     24 |         101.43 |         15.5 |                     85.71 | Approved         | No                  | International |
| BK-2026-0041 | NXC-SAL-0102  | Meridian Foods          | 16-04-2026     |                     36 |          80.68 |          1.6 |                     79.39 | Approved         | No                  | South         |
| BK-2026-0042 | NXC-SAL-0105  | Harbor Telecom          | 16-04-2026     |                     12 |         116.15 |         10.5 |                    103.95 | Approved         | No                  | South         |
| BK-2026-0043 | NXC-SAL-0104  | Aster Mobility          | 20-03-2026     |                     36 |          94.48 |          0.8 |                     93.72 | Pending          | No                  | International |
| BK-2026-0044 | NXC-SAL-0103  | Cedar Finance           | 27-01-2026     |                     12 |          44.07 |         19.1 |                     35.65 | Approved         | No                  | South         |
| BK-2026-0045 | NXC-SAL-0102  | Vertex Health           | 23-04-2026     |                     12 |          93.76 |          2.1 |                     91.79 | Approved         | No                  | South         |
| BK-2026-0046 | NXC-SAL-0105  | Solstice Energy         | 06-07-2026     |                     24 |          88.91 |         10.2 |                      0    | Clawed Back      | Yes                 | South         |
| BK-2026-0047 | NXC-SAL-0101  | Aster Mobility          | 12-02-2026     |                     24 |           7.79 |         16.4 |                      6.51 | Approved         | No                  | West          |
| BK-2026-0048 | NXC-SAL-0102  | Quanta Digital          | 19-02-2026     |                     12 |          13.48 |         21.6 |                     10.57 | Pending          | No                  | West          |
| BK-2026-0049 | NXC-SAL-0101  | Vertex Health           | 01-07-2026     |                     36 |          43.75 |         17.7 |                     36.01 | Pending          | No                  | West          |
| BK-2026-0050 | NXC-SAL-0101  | Northstar Manufacturing | 10-07-2026     |                     24 |         114.38 |          5.2 |                    108.43 | Approved         | No                  | North         |
| BK-2026-0051 | NXC-SAL-0106  | Aster Mobility          | 10-03-2026     |                     36 |         109.53 |          1.5 |                    107.89 | Approved         | No                  | South         |
| BK-2026-0052 | NXC-SAL-0105  | Orion Retail Group      | 08-04-2026     |                     36 |         118.51 |         13   |                    103.1  | Approved         | No                  | South         |
| BK-2026-0053 | NXC-SAL-0103  | Meridian Foods          | 05-07-2026     |                     12 |          33.78 |          1.4 |                     33.31 | Approved         | No                  | International |
| BK-2026-0054 | NXC-SAL-0105  | Cedar Finance           | 10-03-2026     |                     24 |          74.83 |         10.6 |                     66.9  | Approved         | No                  | International |
| BK-2026-0055 | NXC-SAL-0101  | Aster Mobility          | 18-03-2026     |                     12 |         108.03 |          6.9 |                      0    | Clawed Back      | Yes                 | International |
| BK-2026-0056 | NXC-SAL-0102  | Harbor Telecom          | 25-07-2026     |                     12 |          12.44 |          2.5 |                     12.13 | Pending          | No                  | South         |
| BK-2026-0057 | NXC-SAL-0101  | Quanta Digital          | 25-07-2026     |                     36 |          44.16 |         10.8 |                     39.39 | Approved         | No                  | West          |
| BK-2026-0058 | NXC-SAL-0104  | Quanta Digital          | 22-04-2026     |                     12 |          14.88 |          7.2 |                     13.81 | Approved         | No                  | South         |
| BK-2026-0059 | NXC-SAL-0102  | BluePeak Logistics      | 22-02-2026     |                     36 |          33.8  |          2.6 |                     32.92 | Approved         | No                  | West          |
| BK-2026-0060 | NXC-SAL-0106  | Solstice Energy         | 01-04-2026     |                     36 |          48.21 |          4.4 |                     46.09 | Approved         | No                  | North         |
| BK-2026-0061 | NXC-SAL-0103  | Orion Retail Group      | 01-05-2026     |                     24 |         107.36 |         21.7 |                     84.06 | Approved         | No                  | West          |
| BK-2026-0062 | NXC-SAL-0102  | Meridian Foods          | 15-07-2026     |                     12 |          26.51 |         18.7 |                      0    | Clawed Back      | Yes                 | International |
| BK-2026-0063 | NXC-SAL-0102  | Quanta Digital          | 16-07-2026     |                     12 |          60.05 |         16.5 |                      0    | Clawed Back      | Yes                 | North         |
| BK-2026-0064 | NXC-SAL-0102  | Harbor Telecom          | 04-06-2026     |                     12 |          53.59 |         15.8 |                     45.12 | Approved         | No                  | South         |
| BK-2026-0065 | NXC-SAL-0106  | BluePeak Logistics      | 04-03-2026     |                     12 |         107.31 |         15.1 |                     91.11 | Approved         | No                  | South         |
| BK-2026-0066 | NXC-SAL-0102  | Cedar Finance           | 11-01-2026     |                     36 |          65.73 |          2.9 |                      0    | Clawed Back      | Yes                 | West          |
| BK-2026-0067 | NXC-SAL-0102  | Meridian Foods          | 16-04-2026     |                     24 |           8.09 |         17.7 |                      6.66 | Pending          | No                  | South         |
| BK-2026-0068 | NXC-SAL-0104  | Cedar Finance           | 06-06-2026     |                     12 |         117.36 |          8.8 |                    107.03 | Pending          | No                  | West          |
| BK-2026-0069 | NXC-SAL-0101  | Harbor Telecom          | 24-06-2026     |                     36 |          91.68 |          1.5 |                     90.3  | Pending          | No                  | North         |
| BK-2026-0070 | NXC-SAL-0106  | Aster Mobility          | 08-04-2026     |                     24 |          97.46 |         16.7 |                     81.18 | Approved         | No                  | West          |
| BK-2026-0071 | NXC-SAL-0104  | Harbor Telecom          | 17-03-2026     |                     12 |          41.43 |         16.1 |                     34.76 | Approved         | No                  | International |
| BK-2026-0072 | NXC-SAL-0101  | Solstice Energy         | 23-01-2026     |                     36 |          90.89 |         13.6 |                      0    | Clawed Back      | Yes                 | International |
| BK-2026-0073 | NXC-SAL-0104  | Meridian Foods          | 01-04-2026     |                     36 |          18.53 |         21.8 |                      0    | Clawed Back      | Yes                 | West          |
| BK-2026-0074 | NXC-SAL-0102  | Solstice Energy         | 28-01-2026     |                     36 |          69.07 |         21.3 |                     54.36 | Pending          | No                  | International |
| BK-2026-0075 | NXC-SAL-0105  | Vertex Health           | 08-04-2026     |                     36 |          41.08 |         15.9 |                     34.55 | Approved         | No                  | North         |
| BK-2026-0076 | NXC-SAL-0104  | Vertex Health           | 23-03-2026     |                     24 |          78.91 |          2   |                     77.33 | Approved         | No                  | West          |
| BK-2026-0077 | NXC-SAL-0104  | BluePeak Logistics      | 08-01-2026     |                     24 |          29.48 |         20.3 |                     23.5  | Approved         | No                  | South         |
| BK-2026-0078 | NXC-SAL-0102  | Quanta Digital          | 19-06-2026     |                     12 |          27.45 |         10.4 |                     24.6  | Approved         | No                  | International |
| BK-2026-0079 | NXC-SAL-0101  | Cedar Finance           | 28-05-2026     |                     36 |         117.54 |         21   |                     92.86 | Approved         | No                  | South         |
| BK-2026-0080 | NXC-SAL-0105  | BluePeak Logistics      | 06-04-2026     |                     12 |          83.58 |          1.6 |                     82.24 | Approved         | No                  | International |
| BK-2026-0081 | NXC-SAL-0101  | Aster Mobility          | 27-07-2026     |                     24 |          99.81 |          4.8 |                     95.02 | Pending          | No                  | West          |
| BK-2026-0082 | NXC-SAL-0102  | BluePeak Logistics      | 21-06-2026     |                     36 |          28.89 |         15.8 |                     24.33 | Approved         | No                  | West          |
| BK-2026-0083 | NXC-SAL-0105  | Meridian Foods          | 28-01-2026     |                     24 |          81.04 |          8.8 |                     73.91 | Approved         | No                  | South         |
| BK-2026-0084 | NXC-SAL-0106  | Harbor Telecom          | 12-03-2026     |                     36 |          89.98 |         17.3 |                     74.41 | Pending          | No                  | South         |
| BK-2026-0085 | NXC-SAL-0106  | Meridian Foods          | 23-02-2026     |                     36 |          65.44 |          1.7 |                     64.33 | Approved         | No                  | North         |
| BK-2026-0086 | NXC-SAL-0105  | Northstar Manufacturing | 03-04-2026     |                     24 |         106.95 |         12.2 |                     93.9  | Approved         | No                  | West          |
| BK-2026-0087 | NXC-SAL-0105  | Harbor Telecom          | 10-02-2026     |                     36 |          61.63 |         18.3 |                     50.35 | Approved         | No                  | West          |
| BK-2026-0088 | NXC-SAL-0103  | Vertex Health           | 15-07-2026     |                     12 |           9.67 |         11.4 |                      8.57 | Pending          | No                  | International |
| BK-2026-0089 | NXC-SAL-0104  | Cedar Finance           | 09-04-2026     |                     24 |          51.48 |          1.3 |                     50.81 | Pending          | No                  | North         |
| BK-2026-0090 | NXC-SAL-0101  | Meridian Foods          | 09-02-2026     |                     36 |          23.64 |         11.7 |                      0    | Clawed Back      | Yes                 | North         |
| BK-2026-0091 | NXC-SAL-0102  | BluePeak Logistics      | 06-03-2026     |                     36 |          44.06 |         14.8 |                     37.54 | Approved         | No                  | West          |
| BK-2026-0092 | NXC-SAL-0102  | Orion Retail Group      | 14-06-2026     |                     36 |         100.06 |         14.5 |                      0    | Clawed Back      | Yes                 | International |
| BK-2026-0093 | NXC-SAL-0103  | Vertex Health           | 14-06-2026     |                     12 |          56.21 |         12.6 |                     49.13 | Approved         | No                  | West          |
| BK-2026-0094 | NXC-SAL-0103  | Cedar Finance           | 12-07-2026     |                     12 |          88.05 |         14.5 |                     75.28 | Pending          | No                  | West          |
| BK-2026-0095 | NXC-SAL-0102  | Solstice Energy         | 23-01-2026     |                     12 |         109.22 |         14.1 |                     93.82 | Pending          | No                  | North         |
| BK-2026-0096 | NXC-SAL-0106  | Cedar Finance           | 20-01-2026     |                     36 |          97.19 |          6.7 |                     90.68 | Approved         | No                  | South         |
| BK-2026-0097 | NXC-SAL-0106  | Aster Mobility          | 12-01-2026     |                     36 |          11.23 |         10.5 |                     10.05 | Approved         | No                  | North         |
| BK-2026-0098 | NXC-SAL-0105  | Cedar Finance           | 05-06-2026     |                     36 |          96.72 |         13   |                     84.15 | Approved         | No                  | West          |
| BK-2026-0099 | NXC-SAL-0105  | Cedar Finance           | 14-03-2026     |                     24 |          16.04 |          9.4 |                     14.53 | Approved         | No                  | North         |
| BK-2026-0100 | NXC-SAL-0101  | Harbor Telecom          | 11-02-2026     |                     36 |          99.88 |          3.7 |                     96.18 | Pending          | No                  | International |

*Total records: 100 row(s)*


## Sheet: Plan_Definitions

| Term                   | Definition                                                                                     |
|:-----------------------|:-----------------------------------------------------------------------------------------------|
| Eligible Booking       | Signed, approved commercial booking that meets Revenue Operations eligibility criteria.        |
| Commissionable Booking | Eligible booking after exclusions, cancellations, credits and approved discount treatment.     |
| Attainment             | Commissionable bookings divided by assigned quota.                                             |
| Accelerator            | Multiplier applied to the base commission rate after an attainment threshold.                  |
| Clawback               | Recovery of previously paid commission after cancellation, non-payment or other defined event. |
| Clawback Window        | Number of days after booking during which defined reversal conditions can affect payout.       |

*Total records: 6 row(s)*
