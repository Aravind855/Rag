---
id: nc.finance.expense_categories
title: Expense Categories
type: Specification
description: Authoritative specification defining expense categories for NexaCore
  Finance operations.
tags:
- finance
- specification
status: stable
stale_after: '2027-08-01T00:00:00Z'
version: '1.0'
owners:
- finance-operations@nexacore.internal
generated:
  by: automated-okf-parser-pipeline
  at: '2026-10-14T00:00:00Z'
verified:
  by: Head of Finance Governance
  at: '2026-10-14T00:00:00Z'
sources:
- id: expense_categories-source
  resource: /Datasource/finance/expense_categories.xlsx
  title: Source Document expense_categories.xlsx
---

# Expense Categories


## Sheet: Expense_Categories

| Category Code   | Category      | Subcategory           | Default Limit INR   |   Receipt Required Above INR | Approval Level          | Cost Type   | Tax Sensitive   | Active   |
|:----------------|:--------------|:----------------------|:--------------------|-----------------------------:|:------------------------|:------------|:----------------|:---------|
| TRV-AIR         | Travel        | Domestic Airfare      | Actuals             |                         1000 | Manager                 | Variable    | Yes             | Yes      |
| TRV-HOT         | Travel        | Domestic Hotel        | 6500                |                         1000 | Function Head           | Variable    | Yes             | Yes      |
| TRV-MEA         | Travel        | Meals                 | 1200                |                         1000 | Manager                 | Variable    | Yes             | Yes      |
| TRV-LOC         | Travel        | Local Transport       | 1500                |                         1000 | Manager                 | Variable    | No              | Yes      |
| CLT-MEA         | Client        | Client Meal           | 3500                |                         1000 | Manager + Function      | Variable    | Yes             | Yes      |
| TEAM-EVT        | People        | Team Event            | 2500                |                         1000 | Manager                 | Variable    | Yes             | Yes      |
| SW-SUB          | Software      | Subscription          | 25000               |                         1000 | Manager + Finance       | Opex        | Yes             | Yes      |
| EQ-MON          | Equipment     | Monitor               | 25000               |                         1000 | Manager + IT            | Capex/Opex  | Yes             | Yes      |
| EQ-ERG          | Equipment     | Ergonomic Chair       | 30000               |                         1000 | Manager + IT            | Capex/Opex  | Yes             | Yes      |
| EQ-MOB          | Equipment     | Mobile Device         | 35000               |                         1000 | Function Head + IT      | Capex       | Yes             | Yes      |
| LNG-CERT        | Learning      | Certification         | 20000               |                         1000 | Manager                 | Opex        | Yes             | Yes      |
| LNG-CONF        | Learning      | Conference            | 25000               |                         1000 | Manager + Function      | Opex        | Yes             | Yes      |
| OFF-SUP         | Office        | General Supplies      | 5000                |                         1000 | Manager                 | Opex        | Yes             | Yes      |
| TEL-MOB         | Communication | Mobile Expense        | 800                 |                          500 | Manager                 | Opex        | Yes             | Yes      |
| TEL-INT         | Communication | Internet              | 1500                |                          500 | Manager                 | Opex        | Yes             | Yes      |
| VIS-FEE         | Travel        | Visa Fee              | 20000               |                         1000 | Function Head + Finance | Variable    | Yes             | Yes      |
| INS-TRV         | Travel        | Travel Insurance      | 10000               |                         1000 | Manager                 | Variable    | Yes             | Yes      |
| BANK-FEE        | Finance       | Bank/Transaction Fee  | 5000                |                         1000 | Finance                 | Opex        | Yes             | Yes      |
| PRO-FEE         | Professional  | Professional Services | 100000              |                         1000 | Function Head + Finance | Opex        | Yes             | Yes      |
| MKT-EVT         | Marketing     | Event Registration    | 75000               |                         1000 | Function Head + Finance | Opex        | Yes             | Yes      |

*Total records: 20 row(s)*


## Sheet: FY27_Budget

| Department       |   FY26 Actual INR Cr |   FY27 Budget INR Cr |   Budget Change % |   Travel % |   Software % |   Professional % | Owner                       | Review Cadence   |
|:-----------------|---------------------:|---------------------:|------------------:|-----------:|-------------:|-----------------:|:----------------------------|:-----------------|
| Engineering      |                 6.75 |                 7.26 |             0.076 |       0.34 |         0.18 |             0.14 | Engineering Finance Partner | Monthly          |
| Data & AI        |                10.31 |                11.43 |             0.109 |       0.27 |         0.16 |             0.05 | Data Finance Partner        | Monthly          |
| Product          |                12.83 |                14.78 |             0.152 |       0.27 |         0.2  |             0.09 | Product Finance Partner     | Monthly          |
| Sales            |                 2.5  |                 2.45 |            -0.021 |       0.12 |         0.13 |             0.08 | Sales Finance Partner       | Monthly          |
| Customer Success |                 2.3  |                 2.53 |             0.102 |       0.27 |         0.16 |             0.07 | CS Finance Partner          | Monthly          |
| Finance          |                 2.4  |                 2.51 |             0.046 |       0.25 |         0.08 |             0.12 | Controller                  | Monthly          |
| Human Resources  |                10.85 |                11.33 |             0.044 |       0.44 |         0.08 |             0.09 | People Finance Partner      | Monthly          |
| Operations       |                 4.26 |                 4.98 |             0.168 |       0.2  |         0.13 |             0.07 | Operations Finance Partner  | Monthly          |
| Security         |                 8.38 |                 8.63 |             0.03  |       0.56 |         0.18 |             0.12 | Security Finance Partner    | Monthly          |
| IT               |                 4.13 |                 4.4  |             0.066 |       0.16 |         0.15 |             0.06 | IT Finance Partner          | Monthly          |

*Total records: 10 row(s)*


## Sheet: Claim_Sample_FY26

| Claim ID      | Employee ID   | Claim Date   | Category Code   | Merchant       |   Amount INR | Cost Center   | Approval Status   | Finance Status   |   Submitted Days After | Exception Code   |
|:--------------|:--------------|:-------------|:----------------|:---------------|-------------:|:--------------|:------------------|:-----------------|-----------------------:|:-----------------|
| EXP-2026-0001 | NXC-CHE-0051  | 08-06-2026   | PRO-FEE         | OfficeHub      |     21510.9  | PRD           | Approved          | Paid             |                     17 | NONE             |
| EXP-2026-0002 | NXC-CHE-0029  | 16-05-2026   | TRV-MEA         | AirVista       |      6953.89 | SAL           | Approved          | Paid             |                      3 | NONE             |
| EXP-2026-0003 | NXC-PUN-0035  | 08-06-2026   | PRO-FEE         | BlueCab        |     54257.1  | FIN           | Pending Review    | Pending          |                      3 | EX01             |
| EXP-2026-0004 | NXC-CHE-0033  | 28-05-2026   | PRO-FEE         | FoodSquare     |     32856.9  | SAL           | Approved          | Paid             |                     48 | NONE             |
| EXP-2026-0005 | NXC-PUN-0077  | 17-05-2026   | TEL-INT         | BlueCab        |     40075    | DAI           | Approved          | Paid             |                      3 | NONE             |
| EXP-2026-0006 | NXC-CHE-0109  | 11-05-2026   | INS-TRV         | CloudMart      |     29021.2  | ENG           | Approved          | Paid             |                      3 | NONE             |
| EXP-2026-0007 | NXC-HYD-0131  | 21-05-2026   | INS-TRV         | Hotel Meridian |     44819.3  | SAL           | Approved          | Paid             |                      3 | NONE             |
| EXP-2026-0008 | NXC-BLR-0075  | 19-04-2026   | VIS-FEE         | FoodSquare     |     53091.5  | SAL           | Approved          | Paid             |                      3 | NONE             |
| EXP-2026-0009 | NXC-PUN-0048  | 14-01-2026   | INS-TRV         | CityRail       |     21747.8  | FIN           | Approved          | Paid             |                     17 | NONE             |
| EXP-2026-0010 | NXC-HYD-0017  | 09-06-2026   | MKT-EVT         | AirVista       |     64395.6  | ENG           | Returned          | Pending          |                      8 | EX01             |
| EXP-2026-0011 | NXC-CHE-0155  | 13-05-2026   | TRV-LOC         | CloudMart      |     47375    | FIN           | Approved          | Paid             |                     17 | NONE             |
| EXP-2026-0012 | NXC-PUN-0035  | 03-06-2026   | LNG-CERT        | FoodSquare     |     25688.5  | DAI           | Approved          | Paid             |                      3 | NONE             |
| EXP-2026-0013 | NXC-BLR-0084  | 10-01-2026   | TRV-AIR         | BlueCab        |     26220.7  | SAL           | Approved          | Paid             |                      8 | NONE             |
| EXP-2026-0014 | NXC-CHE-0082  | 19-06-2026   | VIS-FEE         | TechCerts      |     34190.1  | OPS           | Approved          | Paid             |                      3 | NONE             |
| EXP-2026-0015 | NXC-HYD-0092  | 23-02-2026   | LNG-CONF        | TechCerts      |     11688.3  | SAL           | Approved          | Paid             |                      3 | NONE             |
| EXP-2026-0016 | NXC-PUN-0081  | 07-03-2026   | TEL-MOB         | TechCerts      |     33281.7  | DAI           | Approved          | Paid             |                     29 | NONE             |
| EXP-2026-0017 | NXC-CHE-0104  | 09-02-2026   | EQ-ERG          | CityRail       |      9906.71 | OPS           | Pending Review    | Pending          |                     35 | EX01             |
| EXP-2026-0018 | NXC-CHE-0136  | 27-06-2026   | TEAM-EVT        | OfficeHub      |     28383.9  | FIN           | Approved          | Paid             |                      3 | NONE             |
| EXP-2026-0019 | NXC-BLR-0001  | 14-02-2026   | VIS-FEE         | FoodSquare     |      2792.35 | SAL           | Approved          | Paid             |                     17 | NONE             |
| EXP-2026-0020 | NXC-PUN-0122  | 03-02-2026   | EQ-MON          | BlueCab        |     17025.4  | SAL           | Approved          | Paid             |                      3 | NONE             |
| EXP-2026-0021 | NXC-PUN-0116  | 25-02-2026   | TEL-MOB         | TechCerts      |     40715    | SAL           | Pending Review    | Pending          |                     35 | EX04             |
| EXP-2026-0022 | NXC-HYD-0030  | 13-03-2026   | MKT-EVT         | FoodSquare     |     43232.6  | FIN           | Approved          | Paid             |                      3 | NONE             |
| EXP-2026-0023 | NXC-HYD-0035  | 13-02-2026   | EQ-MON          | Hotel Meridian |     52820.8  | FIN           | Pending Review    | Pending          |                      8 | EX01             |
| EXP-2026-0024 | NXC-HYD-0080  | 10-02-2026   | SW-SUB          | Hotel Meridian |     43687.9  | DAI           | Returned          | Pending          |                     35 | EX01             |
| EXP-2026-0025 | NXC-HYD-0083  | 20-05-2026   | EQ-ERG          | AirVista       |      1456.19 | ENG           | Approved          | Paid             |                     17 | NONE             |
| EXP-2026-0026 | NXC-CHE-0046  | 01-04-2026   | TEAM-EVT        | CloudMart      |     32859.8  | OPS           | Approved          | Paid             |                      3 | NONE             |
| EXP-2026-0027 | NXC-PUN-0135  | 20-01-2026   | SW-SUB          | CityRail       |     60355.1  | FIN           | Approved          | Paid             |                      3 | NONE             |
| EXP-2026-0028 | NXC-BLR-0064  | 18-04-2026   | TEAM-EVT        | CityRail       |      1384.5  | ENG           | Approved          | Paid             |                      3 | NONE             |
| EXP-2026-0029 | NXC-BLR-0043  | 14-02-2026   | TRV-HOT         | FoodSquare     |     26245.1  | OPS           | Approved          | Paid             |                     17 | NONE             |
| EXP-2026-0030 | NXC-BLR-0131  | 13-01-2026   | EQ-ERG          | CityRail       |     14583.6  | PRD           | Approved          | Paid             |                      8 | NONE             |
| EXP-2026-0031 | NXC-HYD-0005  | 14-06-2026   | EQ-MON          | AirVista       |     62142.6  | FIN           | Pending Review    | Pending          |                     48 | EX02             |
| EXP-2026-0032 | NXC-BLR-0076  | 07-01-2026   | TRV-MEA         | TechCerts      |      4494.43 | DAI           | Approved          | Paid             |                     17 | NONE             |
| EXP-2026-0033 | NXC-HYD-0077  | 19-03-2026   | PRO-FEE         | AirVista       |       700.26 | DAI           | Approved          | Paid             |                      3 | NONE             |
| EXP-2026-0034 | NXC-BLR-0008  | 19-04-2026   | TRV-LOC         | BlueCab        |     49783.1  | ENG           | Returned          | Pending          |                     48 | EX01             |
| EXP-2026-0035 | NXC-PUN-0034  | 23-04-2026   | EQ-ERG          | CityRail       |     55779.3  | DAI           | Returned          | Pending          |                     29 | EX04             |
| EXP-2026-0036 | NXC-HYD-0081  | 28-03-2026   | TEAM-EVT        | AirVista       |     31363.4  | FIN           | Approved          | Paid             |                     17 | NONE             |
| EXP-2026-0037 | NXC-CHE-0104  | 22-02-2026   | TRV-LOC         | CloudMart      |     39020    | PRD           | Approved          | Paid             |                     17 | NONE             |
| EXP-2026-0038 | NXC-CHE-0050  | 08-03-2026   | EQ-ERG          | CloudMart      |     45617.8  | OPS           | Approved          | Paid             |                      8 | NONE             |
| EXP-2026-0039 | NXC-BLR-0116  | 02-06-2026   | TEL-MOB         | CloudMart      |     50895.2  | DAI           | Pending Review    | Pending          |                      3 | EX04             |
| EXP-2026-0040 | NXC-CHE-0123  | 15-05-2026   | TRV-LOC         | CityRail       |     30378    | PRD           | Approved          | Paid             |                     17 | NONE             |
| EXP-2026-0041 | NXC-HYD-0139  | 13-04-2026   | EQ-ERG          | CityRail       |      7968.58 | PRD           | Approved          | Paid             |                     17 | NONE             |
| EXP-2026-0042 | NXC-HYD-0148  | 11-05-2026   | VIS-FEE         | FoodSquare     |     44712.3  | SAL           | Approved          | Paid             |                      3 | NONE             |
| EXP-2026-0043 | NXC-BLR-0039  | 02-02-2026   | INS-TRV         | CloudMart      |     57598.7  | SAL           | Approved          | Paid             |                     17 | NONE             |
| EXP-2026-0044 | NXC-HYD-0022  | 04-05-2026   | CLT-MEA         | Hotel Meridian |     28198.6  | OPS           | Pending Review    | Pending          |                     35 | EX01             |
| EXP-2026-0045 | NXC-PUN-0011  | 12-01-2026   | INS-TRV         | CityRail       |     57688.5  | DAI           | Returned          | Pending          |                      8 | EX02             |
| EXP-2026-0046 | NXC-BLR-0129  | 01-06-2026   | TRV-LOC         | Hotel Meridian |     21265.2  | OPS           | Approved          | Paid             |                      8 | NONE             |
| EXP-2026-0047 | NXC-CHE-0044  | 06-06-2026   | EQ-MOB          | FoodSquare     |     49000.1  | OPS           | Approved          | Paid             |                      8 | NONE             |
| EXP-2026-0048 | NXC-BLR-0093  | 02-03-2026   | INS-TRV         | Hotel Meridian |     58874.2  | PRD           | Approved          | Paid             |                      3 | NONE             |
| EXP-2026-0049 | NXC-HYD-0038  | 17-04-2026   | TRV-HOT         | CityRail       |      9823.21 | PRD           | Returned          | Pending          |                     35 | EX02             |
| EXP-2026-0050 | NXC-CHE-0001  | 14-01-2026   | SW-SUB          | CityRail       |      5623.94 | FIN           | Approved          | Paid             |                      3 | NONE             |
| EXP-2026-0051 | NXC-BLR-0153  | 01-02-2026   | SW-SUB          | BlueCab        |       676.23 | SAL           | Approved          | Paid             |                     29 | NONE             |
| EXP-2026-0052 | NXC-BLR-0081  | 28-02-2026   | TEL-MOB         | AirVista       |     64536.9  | DAI           | Pending Review    | Pending          |                     17 | EX02             |
| EXP-2026-0053 | NXC-BLR-0010  | 12-06-2026   | TEL-INT         | OfficeHub      |     42203.8  | PRD           | Approved          | Paid             |                     29 | NONE             |
| EXP-2026-0054 | NXC-CHE-0019  | 26-03-2026   | SW-SUB          | TechCerts      |     60962.9  | ENG           | Pending Review    | Pending          |                     17 | EX02             |
| EXP-2026-0055 | NXC-HYD-0112  | 04-03-2026   | EQ-MON          | CloudMart      |     28673.1  | OPS           | Approved          | Paid             |                     29 | NONE             |
| EXP-2026-0056 | NXC-CHE-0073  | 05-05-2026   | TRV-LOC         | TechCerts      |     47598.7  | ENG           | Approved          | Paid             |                     17 | NONE             |
| EXP-2026-0057 | NXC-CHE-0089  | 08-03-2026   | PRO-FEE         | CityRail       |     27571.1  | PRD           | Approved          | Paid             |                     17 | NONE             |
| EXP-2026-0058 | NXC-HYD-0106  | 01-06-2026   | EQ-MON          | CloudMart      |     47355.4  | OPS           | Approved          | Paid             |                      3 | NONE             |
| EXP-2026-0059 | NXC-PUN-0021  | 26-03-2026   | EQ-MON          | Hotel Meridian |     58717.5  | ENG           | Approved          | Paid             |                     35 | NONE             |
| EXP-2026-0060 | NXC-CHE-0135  | 26-03-2026   | MKT-EVT         | BlueCab        |     52919.4  | PRD           | Returned          | Pending          |                     17 | EX02             |
| EXP-2026-0061 | NXC-PUN-0136  | 14-06-2026   | PRO-FEE         | FoodSquare     |     42135.6  | ENG           | Approved          | Paid             |                      3 | NONE             |
| EXP-2026-0062 | NXC-CHE-0015  | 21-04-2026   | TEAM-EVT        | TechCerts      |     12396.6  | FIN           | Approved          | Paid             |                      8 | NONE             |
| EXP-2026-0063 | NXC-CHE-0147  | 03-04-2026   | CLT-MEA         | AirVista       |     37966.5  | DAI           | Approved          | Paid             |                     48 | NONE             |
| EXP-2026-0064 | NXC-CHE-0111  | 28-03-2026   | EQ-MOB          | CityRail       |      2665.52 | FIN           | Approved          | Paid             |                     17 | NONE             |
| EXP-2026-0065 | NXC-CHE-0076  | 26-04-2026   | SW-SUB          | CityRail       |      7313.56 | ENG           | Returned          | Pending          |                     35 | EX01             |
| EXP-2026-0066 | NXC-BLR-0092  | 27-02-2026   | INS-TRV         | OfficeHub      |     60410.8  | DAI           | Approved          | Paid             |                     17 | NONE             |
| EXP-2026-0067 | NXC-HYD-0014  | 27-03-2026   | CLT-MEA         | AirVista       |     40686.8  | SAL           | Approved          | Paid             |                     17 | NONE             |
| EXP-2026-0068 | NXC-HYD-0115  | 05-01-2026   | LNG-CERT        | OfficeHub      |     63916.1  | FIN           | Approved          | Paid             |                      3 | NONE             |
| EXP-2026-0069 | NXC-CHE-0037  | 06-06-2026   | EQ-MOB          | BlueCab        |     58263.3  | FIN           | Returned          | Pending          |                     17 | EX02             |
| EXP-2026-0070 | NXC-CHE-0023  | 25-05-2026   | INS-TRV         | OfficeHub      |      8810.58 | SAL           | Approved          | Paid             |                     17 | NONE             |
| EXP-2026-0071 | NXC-PUN-0079  | 13-02-2026   | TRV-AIR         | OfficeHub      |     32334    | SAL           | Approved          | Paid             |                      3 | NONE             |
| EXP-2026-0072 | NXC-PUN-0056  | 24-04-2026   | TEL-INT         | CloudMart      |      6837.64 | SAL           | Approved          | Paid             |                      8 | NONE             |
| EXP-2026-0073 | NXC-PUN-0105  | 27-02-2026   | CLT-MEA         | AirVista       |     29013.8  | DAI           | Approved          | Paid             |                      3 | NONE             |
| EXP-2026-0074 | NXC-BLR-0056  | 22-03-2026   | TEAM-EVT        | AirVista       |     27222.7  | DAI           | Approved          | Paid             |                      3 | NONE             |
| EXP-2026-0075 | NXC-PUN-0098  | 18-06-2026   | TRV-MEA         | CloudMart      |      1070.32 | SAL           | Approved          | Paid             |                     35 | NONE             |
| EXP-2026-0076 | NXC-PUN-0142  | 14-02-2026   | EQ-MON          | OfficeHub      |     40238.4  | FIN           | Approved          | Paid             |                      3 | NONE             |
| EXP-2026-0077 | NXC-HYD-0044  | 21-02-2026   | PRO-FEE         | FoodSquare     |     23516    | DAI           | Approved          | Paid             |                      3 | NONE             |
| EXP-2026-0078 | NXC-PUN-0049  | 20-06-2026   | MKT-EVT         | OfficeHub      |     17671.3  | SAL           | Approved          | Paid             |                      8 | NONE             |
| EXP-2026-0079 | NXC-PUN-0085  | 22-01-2026   | BANK-FEE        | Hotel Meridian |     28756.8  | OPS           | Approved          | Paid             |                     29 | NONE             |
| EXP-2026-0080 | NXC-PUN-0049  | 28-01-2026   | BANK-FEE        | BlueCab        |      8901.84 | FIN           | Approved          | Paid             |                      8 | NONE             |
| EXP-2026-0081 | NXC-CHE-0129  | 25-03-2026   | TEL-MOB         | AirVista       |     28119.1  | ENG           | Approved          | Paid             |                     17 | NONE             |
| EXP-2026-0082 | NXC-CHE-0048  | 13-04-2026   | TEL-INT         | OfficeHub      |     63399.5  | PRD           | Returned          | Pending          |                     35 | EX04             |
| EXP-2026-0083 | NXC-CHE-0110  | 12-01-2026   | TRV-AIR         | AirVista       |     42633.9  | DAI           | Approved          | Paid             |                      8 | NONE             |
| EXP-2026-0084 | NXC-CHE-0150  | 27-03-2026   | OFF-SUP         | AirVista       |     23851.1  | ENG           | Approved          | Paid             |                      3 | NONE             |
| EXP-2026-0085 | NXC-PUN-0099  | 10-06-2026   | VIS-FEE         | CityRail       |     31881.4  | PRD           | Pending Review    | Pending          |                     35 | EX04             |
| EXP-2026-0086 | NXC-PUN-0007  | 16-04-2026   | TRV-HOT         | CityRail       |     62923.8  | OPS           | Pending Review    | Pending          |                      3 | EX02             |
| EXP-2026-0087 | NXC-CHE-0002  | 20-03-2026   | PRO-FEE         | FoodSquare     |     28265.3  | PRD           | Approved          | Paid             |                      3 | NONE             |
| EXP-2026-0088 | NXC-CHE-0023  | 02-02-2026   | TRV-HOT         | CityRail       |     49173.2  | FIN           | Approved          | Paid             |                     29 | NONE             |
| EXP-2026-0089 | NXC-PUN-0141  | 23-03-2026   | LNG-CONF        | TechCerts      |      1312.36 | OPS           | Pending Review    | Pending          |                     35 | EX04             |
| EXP-2026-0090 | NXC-HYD-0132  | 03-05-2026   | EQ-MOB          | BlueCab        |     25300.9  | ENG           | Approved          | Paid             |                      8 | NONE             |
| EXP-2026-0091 | NXC-CHE-0123  | 06-06-2026   | CLT-MEA         | FoodSquare     |     44903.6  | ENG           | Approved          | Paid             |                      8 | NONE             |
| EXP-2026-0092 | NXC-CHE-0036  | 15-04-2026   | LNG-CERT        | OfficeHub      |     22219.1  | OPS           | Approved          | Paid             |                      3 | NONE             |
| EXP-2026-0093 | NXC-HYD-0010  | 24-01-2026   | BANK-FEE        | CityRail       |     45345.3  | OPS           | Approved          | Paid             |                     17 | NONE             |
| EXP-2026-0094 | NXC-HYD-0093  | 27-02-2026   | TRV-AIR         | TechCerts      |      6645.6  | ENG           | Approved          | Paid             |                     29 | NONE             |
| EXP-2026-0095 | NXC-PUN-0112  | 13-04-2026   | EQ-ERG          | CloudMart      |     53323.6  | ENG           | Pending Review    | Pending          |                     29 | EX02             |
| EXP-2026-0096 | NXC-HYD-0101  | 24-04-2026   | TRV-HOT         | FoodSquare     |     47180.5  | PRD           | Approved          | Paid             |                      3 | NONE             |
| EXP-2026-0097 | NXC-BLR-0028  | 12-05-2026   | SW-SUB          | BlueCab        |     57241    | PRD           | Pending Review    | Pending          |                      8 | EX02             |
| EXP-2026-0098 | NXC-PUN-0117  | 22-03-2026   | EQ-MOB          | CityRail       |     15295.2  | FIN           | Approved          | Paid             |                     17 | NONE             |
| EXP-2026-0099 | NXC-PUN-0055  | 16-04-2026   | OFF-SUP         | BlueCab        |     58655.4  | SAL           | Pending Review    | Pending          |                     17 | EX01             |
| EXP-2026-0100 | NXC-HYD-0078  | 17-06-2026   | TRV-LOC         | OfficeHub      |     23683.3  | FIN           | Approved          | Paid             |                      3 | NONE             |

*Total records: 100 row(s)*


## Sheet: Merchant_Controls

| Merchant ID   | Merchant Name   | Category        | Preferred   | Risk Tier   | Contract Status   |   Monthly Spend Limit INR | Review Owner   |
|:--------------|:----------------|:----------------|:------------|:------------|:------------------|--------------------------:|:---------------|
| M-001         | BlueCab         | Local Transport | Yes         | Low         | Active            |                    450000 | Finance Ops    |
| M-002         | Hotel Meridian  | Hotel           | Yes         | Low         | Active            |                    900000 | Travel Desk    |
| M-003         | AirVista        | Airfare         | Yes         | Medium      | Active            |                   1800000 | Travel Desk    |
| M-004         | CloudMart       | Software        | Yes         | Medium      | Active            |                   1200000 | IT Procurement |
| M-005         | OfficeHub       | Office Supplies | Yes         | Low         | Active            |                    350000 | Procurement    |
| M-006         | TechCerts       | Learning        | No          | Low         | Approved Supplier |                    250000 | People Ops     |
| M-007         | FoodSquare      | Meals           | No          | Medium      | Approved Supplier |                    300000 | Finance Ops    |
| M-008         | GlobalStay      | Hotel           | No          | Medium      | Active            |                    700000 | Travel Desk    |

*Total records: 8 row(s)*


## Sheet: Data_Dictionary

| Field                      | Definition                                                                   |
|:---------------------------|:-----------------------------------------------------------------------------|
| Category Code              | Controlled Finance category identifier used by expense workflow.             |
| Default Limit INR          | Standard policy limit before exception or additional approval.               |
| Receipt Required Above INR | Receipt threshold from Finance policy.                                       |
| Approval Level             | Normal approval path; exceptions may require higher authority.               |
| Tax Sensitive              | Whether Finance may need additional tax documentation or treatment.          |
| Claim Sample FY26          | Synthetic sample of transaction-level reimbursement records for RAG testing. |

*Total records: 6 row(s)*
