# AI Python Learning Tracker

A multi-user Python learning tracker built with Streamlit and SQLite. Each account has its own topics, journal entries, dashboard, and tutor context.

## Included features

- Account registration and login. After registration, the app displays **Account created successfully!** and asks the user to log in; it does not automatically sign them in.
- Per-user topic management: add, edit, update, and delete user-defined topics.
- After a topic is added, **Topic added successfully!** appears and the topic input fields are cleared for the next topic.
- Learning journal: create a new entry, edit/update an existing entry, and delete an entry.
- Optional journal-to-topic links. Deleting a topic preserves journal entries and removes only their topic link.
- Dashboard counts for topics, completed topics, and journal entries.
- Optional AI tutor that uses the current user's topics and recent journal notes as learning context.
- Passwords are stored as salted PBKDF2-HMAC-SHA256 hashes, not plain text.

## Run on Windows

1. Install Python 3.10 or newer.
2. Extract the ZIP and open PowerShell in the extracted folder.
3. Create and activate a virtual environment:

   ```powershell
   python -m venv .venv
   .venv\Scripts\Activate.ps1
   ```

4. Install packages:

   ```powershell
   pip install -r requirements.txt
   ```

5. Start the app:

   ```powershell
   streamlit run app.py
   ```

6. Open the local address shown in the terminal, usually http://localhost:8501.

## Enable the AI tutor (optional)

Set your OpenAI API key before starting the app:

```powershell
$env:OPENAI_API_KEY="your-api-key"
streamlit run app.py
```

Without the key, account, topic, journal, and dashboard features still work; AI answers are disabled.

## Data

The SQLite database is created as `tracker.db` in the project directory. To choose another location, set `TRACKER_DB_PATH` before starting Streamlit.

## Deployment warning

This is a local-development MVP, not production-ready public authentication. Before hosting it publicly, add HTTPS, a robust authentication/session provider, rate limiting, managed secrets, backups, and a production database with enforced per-user access controls. Never expose the database file or API key.
