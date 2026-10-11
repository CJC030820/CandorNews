import os
import smtplib

SMTP_HOST = os.getenv("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USERNAME = os.getenv("SMTP_USERNAME")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD")

if not SMTP_USERNAME or not SMTP_PASSWORD:
    raise SystemExit("Set SMTP_USERNAME and SMTP_PASSWORD as environment variables before running this test.")

try:
    print(f"Attempting to connect to {SMTP_HOST}:{SMTP_PORT}...")
    with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=15) as server:
        server.starttls()
        server.login(SMTP_USERNAME, SMTP_PASSWORD)
    print("SMTP login successful.")
except Exception as error:
    print(f"SMTP test failed: {type(error).__name__}: {error}")
