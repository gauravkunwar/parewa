# --- START OF FILE app.py ---

import os
import smtplib
from email.utils import formataddr # Import helper for formatting
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
from flask import Flask, render_template, request, flash, redirect, url_for
from dotenv import load_dotenv
import logging # Import logging library

# Load environment variables from .env file
load_dotenv()

app = Flask(__name__)
# Use env var for secret key or provide a fallback (change fallback for production)
app.secret_key = os.getenv('FLASK_SECRET_KEY', 'a_very_strong_default_secret_key_for_dev')

# Configure basic logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# --- Configuration from Environment Variables ---
SMTP_SERVER = os.getenv('SMTP_SERVER')
SMTP_PORT = int(os.getenv('SMTP_PORT', 587)) # Default to 587 if not set
SMTP_USERNAME = os.getenv('SMTP_USERNAME')
SMTP_PASSWORD = os.getenv('SMTP_PASSWORD')
USE_TLS = os.getenv('USE_TLS', 'true').lower() == 'true'
USE_SSL = os.getenv('USE_SSL', 'false').lower() == 'true'
# --- End Configuration ---


# --- Helper Function for Formatting SMTP Errors ---
def format_smtp_error_message(error_data):
    """Decodes SMTP error data (bytes or str) and cleans it for display."""
    message = ""
    if isinstance(error_data, bytes):
        try:
            # Try decoding as UTF-8, replace errors if decoding fails
            message = error_data.decode('utf-8', errors='replace')
        except Exception as decode_error:
            # Fallback to default string representation if decoding fails badly
            app.logger.warning(f"Could not decode SMTP error bytes: {decode_error}. Falling back to str(). Error data: {error_data}")
            message = str(error_data)
    elif isinstance(error_data, str):
        message = error_data
    else:
        # Handle potential other types just in case
        message = str(error_data)

    # Replace newlines with spaces and strip leading/trailing whitespace
    return message.replace('\n', ' ').strip()
# --- End of helper function ---


# --- Input Validation ---
def validate_config():
    """Checks if essential SMTP configuration is present."""
    errors = []
    if not SMTP_SERVER: errors.append("SMTP_SERVER")
    if not os.getenv('SMTP_PORT'): # Check if it was explicitly set
        app.logger.info("SMTP_PORT not set in .env, using default 587.")
    if not SMTP_USERNAME: errors.append("SMTP_USERNAME")
    if not SMTP_PASSWORD: errors.append("SMTP_PASSWORD")

    if USE_TLS and USE_SSL:
         flash("Configuration error: Cannot use both TLS and SSL. Please set either USE_TLS or USE_SSL to 'false' in your .env file.", "error")
         app.logger.error("Configuration Error: USE_TLS and USE_SSL cannot both be true.")
         return False # Specific check for mutual exclusivity

    if not errors:
        return True
    else:
        error_msg = f"Missing required environment variables: {', '.join(errors)}. Please check your .env file or environment configuration."
        flash(error_msg, "error")
        app.logger.error(error_msg)
        return False

def is_valid_email_list(email_string):
    """Basic check for comma-separated emails."""
    if not email_string:
        return False, "Recipient email ('To') cannot be empty."
    # Split by comma, strip whitespace from each part, filter out empty strings
    emails = [e.strip() for e in email_string.split(',') if e.strip()]
    if not emails:
        return False, "No valid recipient emails provided after parsing."
    # Rudimentary check - real email validation is complex and often done by the mail server
    invalid_emails = []
    for email in emails:
        # Basic checks: contains '@', contains '.' after '@', has content before/after '@'
        parts = email.split('@')
        if len(parts) != 2 or not parts[0] or not parts[1] or '.' not in parts[1]:
             invalid_emails.append(email)
    if invalid_emails:
        return False, f"Invalid email format detected for: {', '.join(invalid_emails)}"
    return True, emails


# --- Routes ---
@app.route('/')
def index():
    """Displays the email form."""
    # Validate config on page load so user knows immediately if setup is wrong
    validate_config()
    return render_template('index.html')

@app.route('/send', methods=['POST'])
def send_email():
    """Handles email sending logic."""
    # Re-validate config on send action as well
    if not validate_config():
        return redirect(url_for('index'))

    # Get form data
    display_name = request.form.get('display_name', '').strip() # Get display name, default to empty, strip whitespace
    from_email_addr = request.form.get('from_email') # The actual email address
    to_email_str = request.form.get('to_email')
    subject = request.form.get('subject')
    body = request.form.get('body')
    attachments = request.files.getlist('attachments') # Handles multiple files

    # Basic validation for required fields before checking email formats
    if not from_email_addr or not to_email_str or not subject or not body:
        flash("Please fill in the 'From Email', 'To', 'Subject', and 'Body' fields.", "error")
        return redirect(url_for('index'))

    # Validate recipient emails first
    is_valid, result = is_valid_email_list(to_email_str)
    if not is_valid:
        flash(result, 'error')
        return redirect(url_for('index'))
    to_emails_list = result # Contains list of validated emails

    # Validate the 'From Email' format itself
    is_from_valid, _ = is_valid_email_list(from_email_addr) # Reuse validation, ignore email list output
    if not is_from_valid:
        # Since 'from_email_addr' should be a single email, the error message from is_valid_email_list might be slightly off
        # Provide a more specific message here.
        flash(f"Invalid format for 'From Email': '{from_email_addr}'", "error")
        return redirect(url_for('index'))


    # --- Construct Email Message ---
    msg = MIMEMultipart()

    # Format the 'From' header with optional display name
    if display_name:
        msg['From'] = formataddr((display_name, from_email_addr))
    else:
        msg['From'] = from_email_addr # Just the email if no display name

    msg['To'] = ", ".join(to_emails_list) # Header 'To' should be a comma-separated string
    msg['Subject'] = subject

    # Attach body
    msg.attach(MIMEText(body, 'plain', 'utf-8')) # Specify encoding

    # Attach files
    for f in attachments:
        # Check if a file was actually selected and has a filename
        if f and f.filename:
            try:
                part = MIMEBase('application', 'octet-stream')
                payload = f.read() # Read file content
                f.seek(0) # Reset file pointer in case it's needed again (though usually not here)
                part.set_payload(payload)
                encoders.encode_base64(part)
                # Ensure filename is ASCII or properly encoded for header
                filename_for_header = f.filename # Store original filename for potential logging
                try:
                    # Try simple ASCII encoding first
                    filename_for_header.encode('ascii')
                    filename_header = f'attachment; filename="{filename_for_header}"'
                except UnicodeEncodeError:
                    # Use RFC 2231 encoding for non-ASCII filenames
                    from email.utils import encode_rfc2231
                    filename_header = f"attachment; filename*={encode_rfc2231(filename_for_header, charset='utf-8')}"
                    app.logger.info(f"Using RFC 2231 encoding for filename: {filename_for_header}")

                part.add_header('Content-Disposition', filename_header)
                msg.attach(part)
                app.logger.info(f"Successfully attached file: {filename_for_header}")
            except Exception as e:
                 # Log the error server-side for debugging
                 app.logger.error(f"Error attaching file '{f.filename}': {e}", exc_info=True)
                 flash(f"Error attaching file '{f.filename}'. Please try again or skip the file.", "error")
                 return redirect(url_for('index'))


    # --- Send Email via SMTP ---
    server = None # Initialize server variable outside try block
    try:
        if USE_SSL:
            # Use SMTP_SSL for connections that are encrypted from the start (usually port 465)
            app.logger.info(f"Connecting via SMTP_SSL to {SMTP_SERVER}:{SMTP_PORT}")
            server = smtplib.SMTP_SSL(SMTP_SERVER, SMTP_PORT, timeout=20) # Increased timeout
        else:
            # Use standard SMTP connection
            app.logger.info(f"Connecting via SMTP to {SMTP_SERVER}:{SMTP_PORT}")
            server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT, timeout=20) # Increased timeout
            # Enable debug output from smtplib if needed (very verbose)
            # server.set_debuglevel(1)
            if USE_TLS:
                # Upgrade the connection to TLS (usually port 587)
                app.logger.info("Starting TLS...")
                server.starttls()
                app.logger.info("TLS started.")

        # Login to the server
        app.logger.info(f"Logging in as {SMTP_USERNAME}...")
        server.login(SMTP_USERNAME, SMTP_PASSWORD)
        app.logger.info("Login successful.")

        # Send the email
        # Note: server.sendmail uses the *envelope sender* (first argument) and a list of recipients.
        # The envelope sender is what the receiving server sees during the SMTP transaction.
        # Using `from_email_addr` here might require 'Send As' permissions on the mail server,
        # especially if it differs from `SMTP_USERNAME`.
        # If sending fails (e.g., Sender Refused), the most compatible option is often to use SMTP_USERNAME here.
        envelope_sender = from_email_addr # Or change to SMTP_USERNAME if permission issues arise
        app.logger.info(f"Sending email. From (envelope): {envelope_sender}, To: {to_emails_list}, From (header): {msg['From']}, Subject: {subject}")
        server.sendmail(envelope_sender, to_emails_list, msg.as_string())
        app.logger.info("Email sent successfully.")

        flash(f"Email successfully sent to: {', '.join(to_emails_list)}!", "success")

    except smtplib.SMTPAuthenticationError:
        app.logger.error("SMTP Authentication Error.", exc_info=False) # exc_info=False hides traceback for security
        flash("SMTP Authentication Error: Incorrect username or password. Please check your .env file.", "error")
    except smtplib.SMTPServerDisconnected:
        app.logger.error("SMTP Server Disconnected.", exc_info=True)
        flash("SMTP Server Disconnected unexpectedly. Please check server status and configuration.", "error")
    except smtplib.SMTPConnectError as e:
        app.logger.error(f"SMTP Connection Error: {e}", exc_info=True)
        flash(f"SMTP Connection Error: Could not connect to {SMTP_SERVER}:{SMTP_PORT}. Check server address, port, and firewall settings.", "error")
    except smtplib.SMTPRecipientsRefused as e:
        app.logger.error(f"SMTP Recipient Refused: {e.recipients}", exc_info=False)
        refused_dict = {}
        for email, (code, msg_bytes) in e.recipients.items():
            refused_dict[email] = f"{code} {format_smtp_error_message(msg_bytes)}"
        refused_str = ", ".join([f"{email}: {reason}" for email, reason in refused_dict.items()])
        flash(f"Recipient(s) refused by server: {refused_str}. Check email addresses.", "error")
    except smtplib.SMTPHeloError as e:
        app.logger.error(f"SMTP HELO/EHLO Error: {e}", exc_info=True)
        server_message = format_smtp_error_message(e.smtp_error)
        flash(f"Server HELO/EHLO Error ({e.smtp_code}): {server_message}. Check server configuration.", "error")
    except smtplib.SMTPSenderRefused as e:
        app.logger.error(f"SMTP Sender Refused: {e.sender}", exc_info=False)
        server_message = format_smtp_error_message(e.smtp_error)
        flash(f"Sender address '{e.sender}' refused by server ({e.smtp_code}): '{server_message}'. Check 'From Email' or server permissions (may need to use authenticated user '{SMTP_USERNAME}' as sender).", "error")
    except smtplib.SMTPDataError as e:
         # *** MODIFIED BLOCK ***
         app.logger.error(f"SMTP Data Error: Code={e.smtp_code}, Msg={e.smtp_error}", exc_info=False)
         # Use the helper function to get a clean message
         server_message = format_smtp_error_message(e.smtp_error)

         # Construct a more readable flash message
         flash_msg = f"Server Data Error ({e.smtp_code}): The server refused the message data."
         if server_message:
              # Add the server's reason if available
              flash_msg += f" Reason: '{server_message}'"

         # Add specific advice for the common "domain not verified" error
         lower_server_msg = server_message.lower()
         if "domain not verified" in lower_server_msg or "sender verification" in lower_server_msg or "sender address rejected" in lower_server_msg:
              flash_msg += f" Please ensure the 'From Email' address ('{from_email_addr}') or its domain is verified or permitted by your email provider (e.g., in 'Verified Senders' settings)."

         flash(flash_msg, "error")
         # *** END OF MODIFIED BLOCK ***
    except TimeoutError:
        app.logger.error(f"SMTP Timeout Error connecting/sending to {SMTP_SERVER}:{SMTP_PORT}", exc_info=True)
        flash("SMTP Timeout Error: The connection timed out. Check server address, port, and network connectivity.", "error")
    except OSError as e:
        # Catch potential network/socket errors not covered by smtplib exceptions
        app.logger.error(f"Network/OS Error: {e}", exc_info=True)
        flash(f"Network Error: Could not communicate with the server ({e}). Check network connection and firewall.", "error")
    except Exception as e:
        # Catch other potential errors (unexpected library errors, etc.)
        app.logger.error(f"An unexpected error occurred: {e}", exc_info=True)
        flash(f"An unexpected error occurred: {type(e).__name__}. Please check the application logs for details.", "error")
    finally:
        # Ensure the server connection is closed if it was established
        if server:
            try:
                app.logger.info("Closing SMTP connection.")
                server.quit()
            except smtplib.SMTPServerDisconnected:
                 app.logger.info("Server already disconnected during quit.")
                 pass # Ignore if already disconnected
            except Exception as e:
                 # Log error during quit but don't prevent redirect
                 app.logger.error(f"Error during server.quit(): {e}", exc_info=True)
                 pass # Ignore other potential errors during quit

    return redirect(url_for('index'))

if __name__ == '__main__':
    # Make sure Flask listens on all interfaces for Docker/network access
    # Debug should be False in production containers
    # Set debug=True ONLY for local development if you need interactive debugging
    # IMPORTANT: Never run with debug=True in a production environment!
    is_debug_mode = os.getenv('FLASK_DEBUG', 'false').lower() == 'true'
    app.run(host='0.0.0.0', port=5000, debug=is_debug_mode)

# --- END OF FILE app.py ---