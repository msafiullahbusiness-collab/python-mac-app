import csv
import json

INPUT_CSV = "Final data.csv"
OUTPUT_CSV = "cleaned_users_fixed.csv"

def clean_csv(input_file, output_file):
    seen = set()
    cleaned_rows = []

    with open(input_file, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            # 🔹 Clean ID (.0 remove)
            if row.get("id"):
                try:
                    # Convert safely to int (even if it’s a float string like '519306272.0')
                    row["id"] = str(int(float(row["id"])))
                except ValueError:
                    row["id"] = row["id"].strip()

            # 🔹 Clean link (remove .0 from the end if present)
            if row.get("profile_link"):
                row["profile_link"] = row["profile_link"].replace(".0", "")

            # 🔹 Deduplicate by ID
            if row["id"] not in seen:
                seen.add(row["id"])
                cleaned_rows.append(row)

    # 🔹 Write cleaned data back
    fieldnames = cleaned_rows[0].keys() if cleaned_rows else []
    with open(output_file, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(cleaned_rows)

    print(f"✅ Cleaned {len(cleaned_rows)} unique rows saved to {output_file}")

clean_csv(INPUT_CSV, OUTPUT_CSV)
