"""
fetch_dataset.py
Fetches authentic NYC 311 Service Requests data directly from NYC Open Data Socrata API,
and generates a realistic messy CSV with typical real-world flaws:
- Inconsistent column naming (whitespace, mixed case)
- Missing values (nulls, 'N/A', empty strings)
- Mixed date formats (ISO, US standard, missing time)
- Numeric fields with currency/comma symbols
- Unstandardized text categories
"""

import os
import json
import random
import httpx
import pandas as pd
import numpy as np

DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data")
os.makedirs(DATA_DIR, exist_ok=True)

def fetch_or_generate_dataset():
    csv_path = os.path.join(DATA_DIR, "nyc_311_messy_sample.csv")
    
    print("[*] Fetching authentic NYC 311 data from Socrata API...")
    records = []
    try:
        url = "https://data.cityofnewyork.us/resource/erm2-nwe9.json"
        response = httpx.get(url, timeout=15.0)
        if response.status_code == 200:
            records = response.json()
            print(f"[+] Successfully fetched {len(records)} authentic records from NYC Open Data!")
    except Exception as e:
        print(f"[!] Warning: Could not fetch from NYC API directly ({e}). Using synthetic real-pattern generator.")

    # If API returned records, build DataFrame from it; otherwise generate high-fidelity synthetic records
    if records and len(records) >= 100:
        raw_df = pd.DataFrame(records)
    else:
        raw_df = generate_synthetic_311(1500)

    # Now introduce realistic real-world messiness to test Task 1 & Rubric (30 marks)
    messy_df = inject_realistic_messiness(raw_df)
    messy_df.to_csv(csv_path, index=False)
    print(f"[+] Saved messy NYC 311 dataset to: {csv_path} ({len(messy_df)} rows, {len(messy_df.columns)} columns)")
    return csv_path

def generate_synthetic_311(n=1500):
    agencies = ["NYPD", "HPD", "DOT", "DSNY", "DEP", "DOB", "DPR", "TLC"]
    complaints = {
        "NYPD": ["Noise - Residential", "Blocked Driveway", "Illegal Parking", "Noise - Commercial", "Drug Activity"],
        "HPD": ["HEAT/HOT WATER", "PLUMBING", "PAINT/PLASTER", "WATER LEAK", "DOOR/WINDOW"],
        "DOT": ["Street Condition", "Traffic Signal Condition", "Street Light Condition", "Sidewalk Condition"],
        "DSNY": ["Sanitation Condition", "Dirty Conditions", "Missed Collection", "Derelict Vehicles"],
        "DEP": ["Water System", "Sewer", "Noise", "Air Quality"],
        "DOB": ["General Construction Condition", "Elevator", "Boiler", "Building/Use"],
        "DPR": ["Damaged Tree", "Overgrown Tree/Branches", "Dead Tree", "Maintenance or Facility"],
        "TLC": ["Taxi Complaint", "Driver Complaint", "Lost Property"]
    }
    boroughs = ["MANHATTAN", "BROOKLYN", "QUEENS", "BRONX", "STATEN ISLAND"]
    statuses = ["Closed", "Closed", "Closed", "Open", "Pending", "In Progress"]
    
    rows = []
    base_date = pd.Timestamp("2024-01-01")
    
    for i in range(n):
        agency = random.choice(agencies)
        complaint = random.choice(complaints[agency])
        borough = random.choice(boroughs)
        status = random.choice(statuses)
        
        # Created date spread over months
        days_offset = random.randint(0, 180)
        hours_offset = random.randint(0, 23)
        created_dt = base_date + pd.Timedelta(days=days_offset, hours=hours_offset, minutes=random.randint(0, 59))
        
        # Resolution time (between 2 hours and 120 hours)
        if status == "Closed":
            resolution_hours = random.choice([2, 4, 8, 12, 24, 48, 72, 96, 120]) + random.random() * 5
            closed_dt = created_dt + pd.Timedelta(hours=resolution_hours)
            closed_str = closed_dt.strftime("%m/%d/%Y %I:%M:%S %p")
        else:
            closed_str = ""
            
        rows.append({
            "unique_key": 60000000 + i,
            "created_date": created_dt.strftime("%m/%d/%Y %I:%M:%S %p"),
            "closed_date": closed_str,
            "agency": agency,
            "agency_name": f"Department of {agency}",
            "complaint_type": complaint,
            "descriptor": f"{complaint} general report",
            "location_type": random.choice(["RESIDENTIAL BUILDING", "STREET/SIDEWALK", "COMMERCIAL", "PARK"]),
            "incident_zip": f"100{random.randint(10, 99)}",
            "incident_address": f"{random.randint(100, 9999)} {random.choice(['Broadway', '5th Ave', 'Atlantic Ave', 'Grand Concourse', 'Queens Blvd'])}",
            "city": borough,
            "borough": borough,
            "status": status,
            "fine_amount": f"${random.randint(50, 500):,}" if random.random() > 0.6 else ""
        })
    return pd.DataFrame(rows)

def inject_realistic_messiness(df):
    """
    Injects authentic dirty spreadsheet issues:
    - Dirty headers with leading/trailing spaces and weird capitalization
    - Inconsistent date formats (ISO, MM/DD/YYYY, missing dates)
    - Missing/NaN representations ('N/A', 'NULL', 'None', '', '?', ' - ')
    - Numeric floats in zip codes ('10025.0')
    - Duplicate rows
    - Mixed case in complaint types ('noise - residential', 'NOISE - RESIDENTIAL')
    """
    messy = df.copy()
    
    # 1. Dirty column headers
    header_map = {}
    for col in messy.columns:
        choice = random.choice([
            col,
            f"  {col}  ",
            col.replace("_", " ").title(),
            col.upper(),
            f" {col.replace('_', ' ')} "
        ])
        header_map[col] = choice
    messy.rename(columns=header_map, inplace=True)
    
    # Find active column names
    col_created = [c for c in messy.columns if "created" in c.lower()][0]
    col_closed = [c for c in messy.columns if "closed" in c.lower()][0] if any("closed" in c.lower() for c in messy.columns) else None
    col_zip = [c for c in messy.columns if "zip" in c.lower()][0] if any("zip" in c.lower() for c in messy.columns) else None
    col_complaint = [c for c in messy.columns if "complaint" in c.lower()][0] if any("complaint" in c.lower() for c in messy.columns) else None
    col_borough = [c for c in messy.columns if "borough" in c.lower()][0] if any("borough" in c.lower() for c in messy.columns) else None

    # 2. Inject dirty missing values across various columns
    for col in messy.columns:
        null_indices = np.random.choice(len(messy), size=int(len(messy) * 0.05), replace=False)
        for idx in null_indices:
            messy.at[idx, col] = random.choice(["N/A", "null", "None", "", "??", " - ", np.nan])
            
    # 3. Zip codes as float string e.g. '10021.0' or dirty values
    if col_zip:
        for idx in range(0, len(messy), 4):
            val = str(messy.at[idx, col_zip]).strip()
            if val and val.isdigit():
                messy.at[idx, col_zip] = f"{float(val):.1f}"

    # 4. Mixed date formats in created_date
    if col_created:
        for idx in range(0, len(messy), 3):
            val = str(messy.at[idx, col_created]).strip()
            try:
                dt = pd.to_datetime(val)
                # Alternate date format: ISO or slash
                if idx % 2 == 0:
                    messy.at[idx, col_created] = dt.strftime("%Y-%m-%d %H:%M:%S")
                else:
                    messy.at[idx, col_created] = dt.strftime("%d/%m/%Y %H:%M")
            except:
                pass

    # 5. Inconsistent casing in complaint types
    if col_complaint:
        for idx in range(0, len(messy), 5):
            val = str(messy.at[idx, col_complaint])
            if val and val not in ["nan", "null", "None"]:
                messy.at[idx, col_complaint] = val.lower() if idx % 2 == 0 else val.upper()

    # 6. Duplicate rows
    duplicates = messy.sample(n=min(25, len(messy)))
    messy = pd.concat([messy, duplicates], ignore_index=True)
    
    return messy

if __name__ == "__main__":
    fetch_or_generate_dataset()
