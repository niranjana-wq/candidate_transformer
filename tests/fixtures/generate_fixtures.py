import os
import json
import csv
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter

FIXTURES_DIR = os.path.dirname(os.path.abspath(__file__))

def create_pdf(filename, text_lines):
    path = os.path.join(FIXTURES_DIR, filename)
    c = canvas.Canvas(path, pagesize=letter)
    y = 750
    for line in text_lines:
        c.drawString(72, y, line)
        y -= 20
    c.save()

def create_corrupted_pdf(filename):
    path = os.path.join(FIXTURES_DIR, filename)
    with open(path, 'wb') as f:
        f.write(b"%PDF-1.4\n")
        f.write(b"This is a corrupted PDF file that cannot be parsed properly.\n")
        f.write(b"garbage" * 100)

def create_json(filename, data):
    path = os.path.join(FIXTURES_DIR, filename)
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

def create_csv(filename, rows):
    path = os.path.join(FIXTURES_DIR, filename)
    with open(path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerows(rows)

def generate_all():
    # 1. Valid Resume (PDF)
    create_pdf("valid_resume.pdf", [
        "name: Johnathan Doe",
        "email: j.doe@test.com",
        "phone: +1 415-555-2671",
        "location: US",
        "skills: Python, Machine Learning"
    ])

    # 2. Corrupted PDF
    create_corrupted_pdf("corrupted.pdf")

    # 3. Scanned/OCR PDF (No extractable text)
    create_pdf("scanned_ocr.pdf", []) # Just an empty canvas simulating an image-only PDF

    # 4. Empty PDF
    create_pdf("empty.pdf", [])

    # 5. Malformed JSON
    with open(os.path.join(FIXTURES_DIR, "malformed.json"), 'w', encoding='utf-8') as f:
        f.write("{ \"name\": \"Bob\", missing_quotes: true ") # Invalid syntax

    # 6. Malformed CSV
    with open(os.path.join(FIXTURES_DIR, "malformed.csv"), 'w', encoding='utf-8') as f:
        f.write("name,email\nAlice,alice@test.com\nBob") # Missing columns

    # 7. Duplicate Candidate Records (JSON)
    create_json("duplicate_records.json", [
        {"name": "Alice Smith", "email": "alice@smith.com", "phone": "12345"},
        {"name": "Alice M. Smith", "email": "alice@smith.com", "experience": [{"company": "Tech"}]}
    ])

    # 8. Unicode Names (JSON)
    create_json("unicode_names.json", [
        {"name": "Иван Петров", "email": "ivan@russia.com"},
        {"name": "佐藤 健", "email": "ken@japan.com"}
    ])

    # 9. Missing Required Fields
    create_json("missing_fields.json", [
        {"email": "no_name@test.com"} # Name is missing
    ])

    # 10. Conflicting Data Arrays (JSON)
    create_json("conflicting_arrays.json", [
        {"name": "Conflict", "email": "c@c.com", "skills": ["Python", "Java"]},
        {"name": "Conflict", "email": "c@c.com", "skills": ["C++", "Go"]}
    ])

    # 11. Oversized Resume (TXT)
    with open(os.path.join(FIXTURES_DIR, "oversized.txt"), 'w', encoding='utf-8') as f:
        f.write("name: Giant Resume\nemail: giant@test.com\n")
        f.write("experience: " + "a very long string " * 10000)

if __name__ == "__main__":
    generate_all()
    print("Fixtures generated successfully.")
