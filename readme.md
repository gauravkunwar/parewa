# Parewa - SMTP Client

A simple web-based SMTP client built with Flask and packaged with Docker. It allows you to send emails (including attachments) via a configured SMTP server through an easy-to-use web interface.

## Features

*   Send emails specifying From (including optional Display Name), To, Subject, and Body.
*   Support for multiple recipients (comma-separated in the 'To' field).
*   Attach multiple files to your emails.
*   Configuration driven entirely by environment variables (`.env` file).
*   Uses Gunicorn for running the Flask application (more robust than the development server).

## Prerequisites

Before you begin, ensure you have the following installed on your system:

*   [Docker](https://docs.docker.com/get-docker/)
*   [Docker Compose](https://docs.docker.com/compose/install/) (v1.28.0+ recommended. Often included with Docker Desktop).

## Setup

1.  **Clone the Repository** (If you haven't already):
    ```bash
    git clone https://github.com/gauravkunwar/parewa.git
    cd parewa
    ```
    If you just have the files, navigate to the directory containing `docker-compose.yml`, `Dockerfile`, `app.py`, etc.

2.  **Configure Environment Variables:**
    Create a file named `.env` in the project root directory (the same directory as `docker-compose.yml`). This file will hold your sensitive SMTP credentials and configuration. **Do not commit this file to Git!** Add `.env` to your `.gitignore` file if using version control.

    Populate the `.env` file with the following variables, replacing the placeholder values with your actual details:

    ```dotenv
    # --- .env file contents ---

    # === SMTP Server Configuration ===
    # Your SMTP server address (e.g., smtp.gmail.com, smtp.office365.com)
    SMTP_SERVER=smtp.example.com

    # Common ports: 587 (for TLS/STARTTLS), 465 (for SSL), 25 (often unencrypted/blocked)
    SMTP_PORT=587

    # Your SMTP login username (often your full email address)
    SMTP_USERNAME=your_email@example.com_or_username

    # Your SMTP password or App Password (RECOMMENDED for services like Gmail/Outlook)
    SMTP_PASSWORD=your_secret_smtp_password_or_app_password

    # Set to 'true' to use STARTTLS encryption (commonly with port 587)
    # Set to 'false' if using direct SSL or no encryption.
    USE_TLS=true

    # Set to 'true' to use direct SSL encryption (commonly with port 465)
    # Set to 'false' if using STARTTLS or no encryption.
    # NOTE: USE_TLS and USE_SSL cannot both be true.
    USE_SSL=false

    # === Flask Application Configuration ===
    # A strong, random secret key for Flask session security.
    # Generate one using: python -c 'import secrets; print(secrets.token_hex(16))'
    FLASK_SECRET_KEY=replace_with_a_strong_random_secret_key

    # Optional: Set Flask debug mode (should be 'false' for normal use)
    # Setting to 'true' is useful ONLY for development/debugging.
    # FLASK_DEBUG=false
    # --- End of .env file ---
    ```

    **Security Notes:**
    *   For services like Gmail or Microsoft 365/Outlook, it's highly recommended to use an **"App Password"** instead of your main account password for better security. Search your provider's help documentation for instructions on generating one.
    *   Ensure `FLASK_SECRET_KEY` is a long, random, and unique string.

## Running the Application

1.  **Build and Start (First time or after code/Dockerfile changes):**
    Open your terminal in the project root directory (where `docker-compose.yml` and `.env` are located) and run:
    ```bash
    docker-compose up --build -d
    ```
    *   `--build`: Forces Docker Compose to build the image based on the `Dockerfile`. This is necessary the first time or if you modify `app.py`, `requirements.txt`, or `Dockerfile`.
    *   `-d`: Runs the container in detached mode (in the background).

2.  **Start (Subsequent times):**
    If the image is already built and no relevant code has changed, you can simply start the application using:
    ```bash
    docker-compose up -d
    ```

## Accessing the Application

Once the container is running successfully, open your web browser and navigate to:

[http://localhost:5001](http://localhost:5001)

*(This assumes you are using the default port mapping `5001:5000` specified in the `docker-compose.yml` file. If you changed the host port (the first number), adjust the URL accordingly.)*

## Stopping the Application

To stop and remove the containers, network, and volumes defined in `docker-compose.yml`, run the following command in the project root directory:

```bash
docker-compose down