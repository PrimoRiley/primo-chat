import sqlite3
import json
from datetime import datetime
from typing import List, Dict, Optional
import os
import uuid
import logging

logger = logging.getLogger(__name__)

class ChatDatabase:
    """SQLite database for storing chat history, documents, and user data per organization."""
    
    def __init__(self, organization_name: str):
        self.organization_name = organization_name
        # Ensure data directory exists
        os.makedirs("/data", exist_ok=True)
        self.db_path = f"/data/{organization_name}.db"
        self._init_db()
    
    def _init_db(self):
        """Initialize all database tables."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Documents table - tracks uploaded documents
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS documents (
                id TEXT PRIMARY KEY,
                filename TEXT NOT NULL,
                openai_file_id TEXT NOT NULL,
                vector_store_id TEXT NOT NULL,
                upload_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                file_size INTEGER,
                status TEXT DEFAULT 'active',
                uploaded_by TEXT
            )
        ''')
        
        # Chat sessions table - tracks individual chat sessions
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS chat_sessions (
                session_id TEXT PRIMARY KEY,
                user_id TEXT,
                thread_id TEXT,
                assistant_id TEXT,
                vector_store_id TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_activity TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                title TEXT DEFAULT 'New Chat',
                status TEXT DEFAULT 'active'
            )
        ''')
        
        # Chat messages table - stores all chat messages
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT,
                role TEXT NOT NULL, -- 'user' or 'assistant'
                content TEXT NOT NULL,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                openai_message_id TEXT,
                metadata TEXT, -- JSON for additional data
                FOREIGN KEY (session_id) REFERENCES chat_sessions (session_id)
            )
        ''')
        
        # Users table - basic user management
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                user_id TEXT PRIMARY KEY,
                email TEXT,
                name TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_login TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                preferences TEXT -- JSON for user preferences
            )
        ''')
        
        # Vector stores table - tracks OpenAI vector stores
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS vector_stores (
                vector_store_id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                document_count INTEGER DEFAULT 0,
                status TEXT DEFAULT 'active'
            )
        ''')
        
        # Create indexes for better performance
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_messages_session_id ON messages(session_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_documents_status ON documents(status)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_sessions_user_id ON chat_sessions(user_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_sessions_last_activity ON chat_sessions(last_activity)')
        
        conn.commit()
        conn.close()
        logger.info(f"Database initialized for organization: {self.organization_name}")
    
    # === VECTOR STORE METHODS ===
    
    def create_vector_store(self, vector_store_id: str, name: str) -> bool:
        """Record a new vector store in the database."""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute('''
                INSERT OR REPLACE INTO vector_stores (vector_store_id, name)
                VALUES (?, ?)
            ''', (vector_store_id, name))
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            logger.error(f"Error creating vector store record: {e}")
            return False
    
    def get_vector_store(self) -> Optional[str]:
        """Get the active vector store ID for this organization."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('''
            SELECT vector_store_id FROM vector_stores 
            WHERE status = 'active' 
            ORDER BY created_at DESC 
            LIMIT 1
        ''')
        result = cursor.fetchone()
        conn.close()
        return result[0] if result else None
    
    # === DOCUMENT METHODS ===
    
    def add_document(self, filename: str, openai_file_id: str, vector_store_id: str, 
                    file_size: int, uploaded_by: str = None) -> bool:
        """Add a document record to the database."""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO documents (id, filename, openai_file_id, vector_store_id, 
                                     file_size, uploaded_by)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (openai_file_id, filename, openai_file_id, vector_store_id, file_size, uploaded_by))
            
            # Update document count in vector store
            cursor.execute('''
                UPDATE vector_stores 
                SET document_count = document_count + 1 
                WHERE vector_store_id = ?
            ''', (vector_store_id,))
            
            conn.commit()
            conn.close()
            logger.info(f"Added document: {filename} ({openai_file_id})")
            return True
        except Exception as e:
            logger.error(f"Error adding document: {e}")
            return False
    
    def list_documents(self) -> List[Dict]:
        """List all active documents for this organization."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('''
            SELECT filename, openai_file_id, upload_date, file_size, uploaded_by
            FROM documents 
            WHERE status = 'active'
            ORDER BY upload_date DESC
        ''')
        
        docs = []
        for row in cursor.fetchall():
            docs.append({
                'filename': row[0],
                'id': row[1],
                'upload_date': row[2],
                'size': row[3],
                'uploaded_by': row[4] or 'Unknown'
            })
        
        conn.close()
        return docs
    
    def delete_document(self, file_id: str) -> bool:
        """Mark a document as deleted."""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Get vector store ID before deletion
            cursor.execute('SELECT vector_store_id FROM documents WHERE openai_file_id = ?', (file_id,))
            result = cursor.fetchone()
            
            # Mark as deleted
            cursor.execute('''
                UPDATE documents 
                SET status = 'deleted' 
                WHERE openai_file_id = ?
            ''', (file_id,))
            
            # Update document count in vector store
            if result:
                cursor.execute('''
                    UPDATE vector_stores 
                    SET document_count = document_count - 1 
                    WHERE vector_store_id = ?
                ''', (result[0],))
            
            conn.commit()
            conn.close()
            logger.info(f"Deleted document: {file_id}")
            return True
        except Exception as e:
            logger.error(f"Error deleting document: {e}")
            return False
    
    def get_document_count(self) -> int:
        """Get total number of active documents."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('SELECT COUNT(*) FROM documents WHERE status = "active"')
        count = cursor.fetchone()[0]
        conn.close()
        return count
    
    # === CHAT SESSION METHODS ===
    
    def create_chat_session(self, session_id: str, user_id: str = None, 
                           thread_id: str = None, assistant_id: str = None,
                           vector_store_id: str = None, title: str = "New Chat") -> str:
        """Create a new chat session."""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute('''
                INSERT OR REPLACE INTO chat_sessions 
                (session_id, user_id, thread_id, assistant_id, vector_store_id, title)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (session_id, user_id, thread_id, assistant_id, vector_store_id, title))
            conn.commit()
            conn.close()
            logger.info(f"Created chat session: {session_id}")
            return session_id
        except Exception as e:
            logger.error(f"Error creating chat session: {e}")
            return session_id
    
    def get_chat_session(self, session_id: str) -> Optional[Dict]:
        """Get chat session details."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('''
            SELECT session_id, user_id, thread_id, assistant_id, vector_store_id, 
                   created_at, last_activity, title, status
            FROM chat_sessions 
            WHERE session_id = ?
        ''', (session_id,))
        
        row = cursor.fetchone()
        conn.close()
        
        if row:
            return {
                'session_id': row[0],
                'user_id': row[1],
                'thread_id': row[2],
                'assistant_id': row[3],
                'vector_store_id': row[4],
                'created_at': row[5],
                'last_activity': row[6],
                'title': row[7],
                'status': row[8]
            }
        return None
    
    def list_chat_sessions(self, user_id: str = None, limit: int = 50) -> List[Dict]:
        """List chat sessions, optionally filtered by user."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        if user_id:
            cursor.execute('''
                SELECT session_id, title, created_at, last_activity, 
                       (SELECT COUNT(*) FROM messages WHERE session_id = cs.session_id) as message_count
                FROM chat_sessions cs
                WHERE user_id = ? AND status = 'active'
                ORDER BY last_activity DESC
                LIMIT ?
            ''', (user_id, limit))
        else:
            cursor.execute('''
                SELECT session_id, title, created_at, last_activity,
                       (SELECT COUNT(*) FROM messages WHERE session_id = cs.session_id) as message_count
                FROM chat_sessions cs
                WHERE status = 'active'
                ORDER BY last_activity DESC
                LIMIT ?
            ''', (limit,))
        
        sessions = []
        for row in cursor.fetchall():
            sessions.append({
                'session_id': row[0],
                'title': row[1],
                'created_at': row[2],
                'last_activity': row[3],
                'message_count': row[4]
            })
        
        conn.close()
        return sessions
    
    def update_session_activity(self, session_id: str):
        """Update the last activity timestamp for a session."""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute('''
                UPDATE chat_sessions 
                SET last_activity = CURRENT_TIMESTAMP 
                WHERE session_id = ?
            ''', (session_id,))
            conn.commit()
            conn.close()
        except Exception as e:
            logger.error(f"Error updating session activity: {e}")
    
    def update_chat_title(self, session_id: str, title: str):
        """Update the title of a chat session."""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute('''
                UPDATE chat_sessions 
                SET title = ? 
                WHERE session_id = ?
            ''', (title, session_id))
            conn.commit()
            conn.close()
            logger.info(f"Updated chat title: {session_id} -> {title}")
        except Exception as e:
            logger.error(f"Error updating chat title: {e}")
    
    # === MESSAGE METHODS ===
    
    def save_message(self, session_id: str, role: str, content: str, 
                    openai_message_id: str = None, metadata: Dict = None) -> bool:
        """Save a message to the database."""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            metadata_json = json.dumps(metadata) if metadata else None
            
            cursor.execute('''
                INSERT INTO messages (session_id, role, content, openai_message_id, metadata)
                VALUES (?, ?, ?, ?, ?)
            ''', (session_id, role, content, openai_message_id, metadata_json))
            
            # Update session last activity
            cursor.execute('''
                UPDATE chat_sessions 
                SET last_activity = CURRENT_TIMESTAMP 
                WHERE session_id = ?
            ''', (session_id,))
            
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            logger.error(f"Error saving message: {e}")
            return False
    
    def get_chat_history(self, session_id: str, limit: int = 50) -> List[Dict]:
        """Get chat history for a session."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('''
            SELECT role, content, timestamp, openai_message_id, metadata
            FROM messages 
            WHERE session_id = ?
            ORDER BY timestamp ASC
            LIMIT ?
        ''', (session_id, limit))
        
        messages = []
        for row in cursor.fetchall():
            metadata = json.loads(row[4]) if row[4] else {}
            messages.append({
                'role': row[0],
                'content': row[1],
                'timestamp': row[2],
                'openai_message_id': row[3],
                'metadata': metadata
            })
        
        conn.close()
        return messages
    
    def get_message_count(self, session_id: str) -> int:
        """Get total message count for a session."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('SELECT COUNT(*) FROM messages WHERE session_id = ?', (session_id,))
        count = cursor.fetchone()[0]
        conn.close()
        return count
    
    # === USER METHODS ===
    
    def create_or_update_user(self, user_id: str, email: str = None, 
                             name: str = None, preferences: Dict = None) -> bool:
        """Create or update a user record."""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            preferences_json = json.dumps(preferences) if preferences else None
            
            cursor.execute('''
                INSERT OR REPLACE INTO users (user_id, email, name, preferences, last_login)
                VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
            ''', (user_id, email, name, preferences_json))
            
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            logger.error(f"Error creating/updating user: {e}")
            return False
    
    def get_user(self, user_id: str) -> Optional[Dict]:
        """Get user details."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('''
            SELECT user_id, email, name, created_at, last_login, preferences
            FROM users 
            WHERE user_id = ?
        ''', (user_id,))
        
        row = cursor.fetchone()
        conn.close()
        
        if row:
            preferences = json.loads(row[5]) if row[5] else {}
            return {
                'user_id': row[0],
                'email': row[1],
                'name': row[2],
                'created_at': row[3],
                'last_login': row[4],
                'preferences': preferences
            }
        return None
    
    # === ANALYTICS/STATS METHODS ===
    
    def get_stats(self) -> Dict:
        """Get database statistics."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Get counts
        cursor.execute('SELECT COUNT(*) FROM documents WHERE status = "active"')
        document_count = cursor.fetchone()[0]
        
        cursor.execute('SELECT COUNT(*) FROM chat_sessions WHERE status = "active"')
        session_count = cursor.fetchone()[0]
        
        cursor.execute('SELECT COUNT(*) FROM messages')
        message_count = cursor.fetchone()[0]
        
        cursor.execute('SELECT COUNT(*) FROM users')
        user_count = cursor.fetchone()[0]
        
        # Get recent activity
        cursor.execute('''
            SELECT COUNT(*) FROM messages 
            WHERE timestamp >= datetime('now', '-24 hours')
        ''')
        messages_24h = cursor.fetchone()[0]
        
        conn.close()
        
        return {
            'documents': document_count,
            'sessions': session_count,
            'messages': message_count,
            'users': user_count,
            'messages_24h': messages_24h,
            'organization': self.organization_name
        }