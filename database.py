import os, sqlite3, hashlib, hmac, secrets
from pathlib import Path

DB_PATH = Path(os.getenv('TRACKER_DB_PATH', Path(__file__).with_name('tracker.db')))

def connect():
    db = sqlite3.connect(DB_PATH)
    db.row_factory = sqlite3.Row
    db.execute('PRAGMA foreign_keys = ON')
    return db

def init_db():
    with connect() as db:
        db.executescript('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL UNIQUE COLLATE NOCASE,
            password_hash TEXT NOT NULL,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS topics (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            title TEXT NOT NULL,
            description TEXT DEFAULT '',
            status TEXT NOT NULL DEFAULT 'Not started',
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS journal (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            topic_id INTEGER REFERENCES topics(id) ON DELETE SET NULL,
            title TEXT NOT NULL,
            content TEXT NOT NULL,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        );
        CREATE INDEX IF NOT EXISTS idx_topics_user ON topics(user_id);
        CREATE INDEX IF NOT EXISTS idx_journal_user ON journal(user_id);
        ''')

def _password_hash(password, salt=None):
    salt = salt or secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), salt, 310000)
    return f'{salt.hex()}${digest.hex()}'

def _password_matches(password, stored):
    salt_hex, digest_hex = stored.split('$', 1)
    candidate = _password_hash(password, bytes.fromhex(salt_hex)).split('$', 1)[1]
    return hmac.compare_digest(candidate, digest_hex)

def register_user(username, password):
    try:
        with connect() as db:
            cur = db.execute('INSERT INTO users(username,password_hash) VALUES (?,?)',
                             (username.strip(), _password_hash(password)))
            return cur.lastrowid
    except sqlite3.IntegrityError:
        raise ValueError('That username is already in use. Please choose another.')

def authenticate_user(username, password):
    with connect() as db:
        row = db.execute('SELECT id, username, password_hash FROM users WHERE username=?',
                         (username.strip(),)).fetchone()
    if row and _password_matches(password, row['password_hash']):
        return row['id'], row['username']
    return None

def get_topics(user_id):
    with connect() as db:
        rows = db.execute('SELECT * FROM topics WHERE user_id=? ORDER BY created_at DESC, id DESC',
                          (user_id,)).fetchall()
    return [dict(row) for row in rows]

def create_topic(user_id, title, description, status):
    with connect() as db:
        db.execute('INSERT INTO topics(user_id,title,description,status) VALUES (?,?,?,?)',
                   (user_id, title, description, status))

def edit_topic(user_id, topic_id, title, description, status):
    with connect() as db:
        db.execute('UPDATE topics SET title=?, description=?, status=? WHERE id=? AND user_id=?',
                   (title, description, status, topic_id, user_id))

def remove_topic(user_id, topic_id):
    # Linked journal entries are retained; their topic link becomes NULL.
    with connect() as db:
        db.execute('DELETE FROM topics WHERE id=? AND user_id=?', (topic_id, user_id))

def get_journal(user_id):
    with connect() as db:
        rows = db.execute('''SELECT j.*, t.title AS topic_title FROM journal j
                             LEFT JOIN topics t ON t.id=j.topic_id
                             WHERE j.user_id=? ORDER BY j.updated_at DESC, j.id DESC''',
                          (user_id,)).fetchall()
    return [dict(row) for row in rows]

def save_journal(user_id, title, content, topic_id=None, entry_id=None):
    with connect() as db:
        if topic_id is not None:
            owned = db.execute('SELECT id FROM topics WHERE id=? AND user_id=?',
                               (topic_id, user_id)).fetchone()
            if not owned:
                raise ValueError('That topic is not part of your account.')
        if entry_id is not None:
            db.execute('''UPDATE journal SET title=?, content=?, topic_id=?, updated_at=CURRENT_TIMESTAMP
                          WHERE id=? AND user_id=?''',
                       (title, content, topic_id, entry_id, user_id))
        else:
            db.execute('INSERT INTO journal(user_id,topic_id,title,content) VALUES (?,?,?,?)',
                       (user_id, topic_id, title, content))

def remove_journal(user_id, entry_id):
    with connect() as db:
        db.execute('DELETE FROM journal WHERE id=? AND user_id=?', (entry_id, user_id))

def dashboard_stats(user_id):
    with connect() as db:
        topic_count = db.execute('SELECT COUNT(*) FROM topics WHERE user_id=?', (user_id,)).fetchone()[0]
        journal_count = db.execute('SELECT COUNT(*) FROM journal WHERE user_id=?', (user_id,)).fetchone()[0]
        completed = db.execute("SELECT COUNT(*) FROM topics WHERE user_id=? AND status='Completed'",
                               (user_id,)).fetchone()[0]
    return topic_count, journal_count, completed
