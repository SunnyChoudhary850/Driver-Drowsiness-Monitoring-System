"""
Email alert sender - replacement for the Twilio SMS module.

Uses Python's built-in smtplib, so there's no paid account or phone number to
buy. Works with Gmail, Outlook, Yahoo, or any SMTP provider.

--- SETUP (Gmail example, easiest option) ---
1. Enable 2-Step Verification on the sending Gmail account:
   https://myaccount.google.com/security
2. Create an "App Password" (Google Account > Security > App passwords).
   This is a 16-character password made just for apps like this one -
   NOT your normal Gmail password.
3. Install python-dotenv:
     pip install python-dotenv
4. Copy ".env.example" to a new file named ".env" in the same folder and fill
   in your real values. This script loads it automatically at startup.
5. Make sure ".env" is listed in your .gitignore so it's never committed or
   made public when you push/deploy this project (a .gitignore is included).

Using a different provider (Outlook, Yahoo, custom SMTP)? Set SMTP_SERVER and
SMTP_PORT in your .env too. (Defaults are Gmail's smtp.gmail.com on port 587.)

You can still use plain OS environment variables instead of a .env file if
you prefer (e.g. in a production/deployment environment) - this script reads
whichever is present.
"""

import os
import smtplib
import ssl
import sys
from email.mime.text import MIMEText

try:
    from dotenv import load_dotenv
    load_dotenv()  # reads a local .env file (if present) into environment variables
except ImportError:
    print("[NOTE] 'python-dotenv' not installed - falling back to system environment "
          "variables only. Run: pip install python-dotenv  (then create a .env file "
          "from .env.example) to load credentials automatically.")

# --- Configuration (from environment variables / .env file - never hardcode credentials) ---
EMAIL_SENDER = os.environ.get("EMAIL_SENDER")
EMAIL_APP_PASSWORD = os.environ.get("EMAIL_APP_PASSWORD")
EMAIL_RECIPIENT = os.environ.get("EMAIL_RECIPIENT")
SMTP_SERVER = os.environ.get("SMTP_SERVER", "smtp.gmail.com")
SMTP_PORT = int(os.environ.get("SMTP_PORT", "587"))


def check_config():
    missing = [name for name, val in [
        ("EMAIL_SENDER", EMAIL_SENDER),
        ("EMAIL_APP_PASSWORD", EMAIL_APP_PASSWORD),
        ("EMAIL_RECIPIENT", EMAIL_RECIPIENT),
    ] if not val]
    if missing:
        print("[ERROR] Missing required environment variables: " + ", ".join(missing))
        print("        See the setup instructions at the top of this file.")
        sys.exit(1)


def send_email_alert(subject: str, body: str):
    """Send an email alert via SMTP."""
    msg = MIMEText(body)
    msg["Subject"] = subject
    msg["From"] = EMAIL_SENDER
    msg["To"] = EMAIL_RECIPIENT

    try:
        context = ssl.create_default_context()
        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.starttls(context=context)
            server.login(EMAIL_SENDER, EMAIL_APP_PASSWORD)
            server.sendmail(EMAIL_SENDER, EMAIL_RECIPIENT, msg.as_string())
        print(f"✅ Email sent to {EMAIL_RECIPIENT}!")
    except smtplib.SMTPAuthenticationError:
        print("❌ Failed to send email: authentication failed. "
              "Double-check EMAIL_SENDER / EMAIL_APP_PASSWORD (must be an App Password, not your normal password).")
    except Exception as e:
        print(f"❌ Failed to send email: {str(e)}")


def send_message(choice):
    """Send message based on user choice."""
    messages = {
        1: ("Drowsiness Alert System - Test", "✅ This is a test email from your Drowsiness Detection System. "
                                                "If you're reading this, email alerts are working correctly."),
        2: ("⚠️ Drowsiness Alert (Test)", "This is a preview of the real alert: drowsiness was detected! "
                                           "The driver's eyes were closed for an extended period. "
                                           "Please check on them immediately."),
        3: ("Drowsiness Alert System - Setup Complete", "🎉 Setup complete! Your Drowsiness Detection System "
                                                          "is now configured to send email alerts when drowsiness is detected."),
        4: (None, "❌ No message sent."),
    }
    subject, body = messages.get(choice, messages[4])
    print(f"\n{body}")

    if choice in [1, 2, 3]:
        send_email_alert(subject, body)


def main():
    check_config()

    print("\n📩 Email Alert Sender")
    print("1. Send Test Email")
    print("2. Send Sample Drowsiness Alert (preview)")
    print("3. Send Setup Complete Message")
    print("4. Exit")

    while True:
        try:
            choice = int(input("\nEnter choice (1-4): "))
            if choice == 4:
                print("\n👋 Goodbye!")
                break
            elif 1 <= choice <= 3:
                send_message(choice)
            else:
                print("⚠️ Invalid choice! Enter 1-4.")
        except ValueError:
            print("⚠️ Please enter a number!")


if __name__ == "__main__":
    main()