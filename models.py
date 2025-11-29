import sqlite3
from datetime import datetime
from typing import List, Dict, Optional
import json
import os
from dotenv import load_dotenv

load_dotenv()

DATABASE_NAME = os.getenv("DATABASE_NAME", "study_buddy.db")

def get_db_connection():
    """Create and return a database connection"""
    conn = sqlite3.connect(DATABASE_NAME)
    conn.row_factory = sqlite3.Row  # Return rows as dictionaries
    return conn

def init_database():
    """Initialize database tables"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Users/Sessions table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id TEXT UNIQUE NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        last_active TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    ''')
    
    # Notes table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS notes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id TEXT NOT NULL,
        filename TEXT NOT NULL,
        original_text TEXT NOT NULL,
        text_length INTEGER,
        uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users(user_id)
    )
    ''')
    
    # Summaries table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS summaries (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        note_id INTEGER NOT NULL,
        user_id TEXT NOT NULL,
        summary_text TEXT NOT NULL,
        summary_type TEXT DEFAULT 'concise',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (note_id) REFERENCES notes(id),
        FOREIGN KEY (user_id) REFERENCES users(user_id)
    )
    ''')
    
    # Quizzes table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS quizzes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        note_id INTEGER NOT NULL,
        user_id TEXT NOT NULL,
        questions TEXT NOT NULL,
        num_questions INTEGER,
        question_type TEXT DEFAULT 'mixed',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (note_id) REFERENCES notes(id),
        FOREIGN KEY (user_id) REFERENCES users(user_id)
    )
    ''')
    
    # Quiz attempts/results table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS quiz_results (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        quiz_id INTEGER NOT NULL,
        user_id TEXT NOT NULL,
        score INTEGER NOT NULL,
        total_questions INTEGER NOT NULL,
        percentage REAL,
        completed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (quiz_id) REFERENCES quizzes(id),
        FOREIGN KEY (user_id) REFERENCES users(user_id)
    )
    ''')
    
    conn.commit()
    conn.close()
    print(f"✅ Database initialized: {DATABASE_NAME}")

# User operations
def create_user(user_id: str) -> bool:
    """Create a new user or update last active time"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('''
        INSERT INTO users (user_id, last_active) 
        VALUES (?, CURRENT_TIMESTAMP)
        ON CONFLICT(user_id) DO UPDATE SET last_active = CURRENT_TIMESTAMP
        ''', (user_id,))
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f"Error creating user: {e}")
        return False

def get_user(user_id: str) -> Optional[Dict]:
    """Get user information"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM users WHERE user_id = ?', (user_id,))
    user = cursor.fetchone()
    conn.close()
    return dict(user) if user else None

# Note operations
def save_note(user_id: str, filename: str, text_content: str) -> Optional[int]:
    """Save uploaded note to database"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('''
        INSERT INTO notes (user_id, filename, original_text, text_length)
        VALUES (?, ?, ?, ?)
        ''', (user_id, filename, text_content, len(text_content)))
        note_id = cursor.lastrowid
        conn.commit()
        conn.close()
        return note_id
    except Exception as e:
        print(f"Error saving note: {e}")
        return None

def get_note(note_id: int) -> Optional[Dict]:
    """Get a specific note"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM notes WHERE id = ?', (note_id,))
    note = cursor.fetchone()
    conn.close()
    return dict(note) if note else None

def get_user_notes(user_id: str, limit: int = 10) -> List[Dict]:
    """Get all notes for a user"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
    SELECT id, filename, text_length, uploaded_at 
    FROM notes 
    WHERE user_id = ? 
    ORDER BY uploaded_at DESC 
    LIMIT ?
    ''', (user_id, limit))
    notes = cursor.fetchall()
    conn.close()
    return [dict(note) for note in notes]

# Summary operations
def save_summary(note_id: int, user_id: str, summary_text: str, summary_type: str = "concise") -> Optional[int]:
    """Save generated summary"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('''
        INSERT INTO summaries (note_id, user_id, summary_text, summary_type)
        VALUES (?, ?, ?, ?)
        ''', (note_id, user_id, summary_text, summary_type))
        summary_id = cursor.lastrowid
        conn.commit()
        conn.close()
        return summary_id
    except Exception as e:
        print(f"Error saving summary: {e}")
        return None

def get_note_summaries(note_id: int) -> List[Dict]:
    """Get all summaries for a note"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
    SELECT * FROM summaries 
    WHERE note_id = ? 
    ORDER BY created_at DESC
    ''', (note_id,))
    summaries = cursor.fetchall()
    conn.close()
    return [dict(summary) for summary in summaries]

# Quiz operations
def save_quiz(note_id: int, user_id: str, questions: List[Dict], question_type: str = "mixed") -> Optional[int]:
    """Save generated quiz"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        questions_json = json.dumps(questions)
        cursor.execute('''
        INSERT INTO quizzes (note_id, user_id, questions, num_questions, question_type)
        VALUES (?, ?, ?, ?, ?)
        ''', (note_id, user_id, questions_json, len(questions), question_type))
        quiz_id = cursor.lastrowid
        conn.commit()
        conn.close()
        return quiz_id
    except Exception as e:
        print(f"Error saving quiz: {e}")
        return None

def get_quiz(quiz_id: int) -> Optional[Dict]:
    """Get a specific quiz"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM quizzes WHERE id = ?', (quiz_id,))
    quiz = cursor.fetchone()
    conn.close()
    if quiz:
        quiz_dict = dict(quiz)
        quiz_dict['questions'] = json.loads(quiz_dict['questions'])
        return quiz_dict
    return None

def get_user_quizzes(user_id: str, limit: int = 10) -> List[Dict]:
    """Get all quizzes for a user"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
    SELECT q.id, q.num_questions, q.question_type, q.created_at, n.filename
    FROM quizzes q
    JOIN notes n ON q.note_id = n.id
    WHERE q.user_id = ?
    ORDER BY q.created_at DESC
    LIMIT ?
    ''', (user_id, limit))
    quizzes = cursor.fetchall()
    conn.close()
    return [dict(quiz) for quiz in quizzes]

# Quiz results operations
def save_quiz_result(quiz_id: int, user_id: str, score: int, total_questions: int) -> Optional[int]:
    """Save quiz attempt result"""
    try:
        percentage = (score / total_questions) * 100 if total_questions > 0 else 0
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('''
        INSERT INTO quiz_results (quiz_id, user_id, score, total_questions, percentage)
        VALUES (?, ?, ?, ?, ?)
        ''', (quiz_id, user_id, score, total_questions, percentage))
        result_id = cursor.lastrowid
        conn.commit()
        conn.close()
        return result_id
    except Exception as e:
        print(f"Error saving quiz result: {e}")
        return None

def get_user_progress(user_id: str) -> Dict:
    """Get user's overall progress statistics"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Total notes
    cursor.execute('SELECT COUNT(*) as count FROM notes WHERE user_id = ?', (user_id,))
    total_notes = cursor.fetchone()['count']
    
    # Total quizzes
    cursor.execute('SELECT COUNT(*) as count FROM quizzes WHERE user_id = ?', (user_id,))
    total_quizzes = cursor.fetchone()['count']
    
    # Average quiz score
    cursor.execute('''
    SELECT AVG(percentage) as avg_score, COUNT(*) as attempts
    FROM quiz_results 
    WHERE user_id = ?
    ''', (user_id,))
    result = cursor.fetchone()
    avg_score = result['avg_score'] or 0
    total_attempts = result['attempts']
    
    # Recent activity
    cursor.execute('''
    SELECT uploaded_at FROM notes 
    WHERE user_id = ? 
    ORDER BY uploaded_at DESC 
    LIMIT 1
    ''', (user_id,))
    last_note = cursor.fetchone()
    last_activity = last_note['uploaded_at'] if last_note else None
    
    conn.close()
    
    return {
        "user_id": user_id,
        "total_notes": total_notes,
        "total_quizzes": total_quizzes,
        "total_attempts": total_attempts,
        "average_score": round(avg_score, 2),
        "last_activity": last_activity
    }

# Initialize database when module is imported
if __name__ == "__main__":
    init_database()