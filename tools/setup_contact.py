"""Asks for the contact the SEC requires from every program that fetches its data, and saves it to .env on this computer.
Run by the installer. Skip it with Enter and the app asks again in the browser the first time you open the US side."""
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import envfile  # noqa: E402

envfile.load()
if envfile.sec_ready():
    print("SEC contact already set. Skipping.")
    sys.exit(0)
print()
print("One quick thing for US stocks. The SEC (the US regulator whose filings power the US company data) asks everyone who")
print("fetches its data by program to say who they are. Enter your own name and email. They stay in the .env file on this")
print("computer and are sent only to the SEC. Press Enter to skip; the app will ask again in the browser.")
print()
name = input("Your name: ").strip()
if not name:
    print("Skipped.")
    sys.exit(0)
while True:
    mail = input("Your email: ").strip()
    if re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", mail):
        break
    print("That does not look like an email address. Try again, or press Ctrl+C to skip.")
envfile.save("SEC_CONTACT_NAME", name)
envfile.save("SEC_CONTACT_EMAIL", mail)
print("Saved.")
