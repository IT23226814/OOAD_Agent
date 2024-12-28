import sqlite3
from datetime import datetime
import json
from typing import Optional, Dict, Any, Union
import logging


class DatabaseManager:
    def __init__(self, db_path: str = "ooad_assistant.db"):
        """Initialize database connection and create tables if they don't exist"""
        self.db_path = db_path
        self.setup_database()

    def get_connection(self):
        """Create and return a database connection"""
        return sqlite3.connect(self.db_path)

    def setup_database(self):
        """Create necessary tables if they don't exist"""
        queries = [
            """
            CREATE TABLE IF NOT EXISTS documents (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                filename TEXT NOT NULL,
                file_type TEXT NOT NULL,
                content BLOB,
                upload_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_accessed TIMESTAMP
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS document_analysis (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                document_id INTEGER,
                analysis_type TEXT NOT NULL,
                analysis_content TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (document_id) REFERENCES documents (id)
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS queries (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                document_id INTEGER,
                query_text TEXT NOT NULL,
                response_text TEXT NOT NULL,
                agent_type TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (document_id) REFERENCES documents (id)
            )
            """
        ]

        with self.get_connection() as conn:
            for query in queries:
                conn.execute(query)

    def save_document(self, filename: str, file_type: str, content: Union[str, bytes]) -> int:
        """Save document to database and return document ID"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    INSERT INTO documents (filename, file_type, content, upload_date, last_accessed)
                    VALUES (?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                    """,
                    (filename, file_type, content)
                )
                return cursor.lastrowid
        except Exception as e:
            logging.error(f"Error saving document: {e}")
            raise

    def get_document(self, document_id: int) -> Optional[Dict[str, Any]]:
        """Retrieve document and update last_accessed timestamp"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    SELECT id, filename, file_type, content, upload_date, last_accessed
                    FROM documents WHERE id = ?
                    """,
                    (document_id,)
                )
                result = cursor.fetchone()

                if result:
                    # Update last accessed timestamp
                    cursor.execute(
                        "UPDATE documents SET last_accessed = CURRENT_TIMESTAMP WHERE id = ?",
                        (document_id,)
                    )

                    return {
                        'id': result[0],
                        'filename': result[1],
                        'file_type': result[2],
                        'content': result[3],
                        'upload_date': result[4],
                        'last_accessed': result[5]
                    }
                return None
        except Exception as e:
            logging.error(f"Error retrieving document: {e}")
            raise

    def save_analysis(self, document_id: int, analysis_type: str, analysis_content: str) -> int:
        """Save document analysis results"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    INSERT INTO document_analysis (document_id, analysis_type, analysis_content)
                    VALUES (?, ?, ?)
                    """,
                    (document_id, analysis_type, analysis_content)
                )
                return cursor.lastrowid
        except Exception as e:
            logging.error(f"Error saving analysis: {e}")
            raise

    def get_analysis(self, document_id: int, analysis_type: str) -> Optional[str]:
        """Retrieve latest analysis for a document"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    SELECT analysis_content FROM document_analysis
                    WHERE document_id = ? AND analysis_type = ?
                    ORDER BY created_at DESC LIMIT 1
                    """,
                    (document_id, analysis_type)
                )
                result = cursor.fetchone()
                return result[0] if result else None
        except Exception as e:
            logging.error(f"Error retrieving analysis: {e}")
            raise

    def save_query(self, document_id: Optional[int], query_text: str,
                   response_text: str, agent_type: str) -> int:
        """Save query and response"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    INSERT INTO queries (document_id, query_text, response_text, agent_type)
                    VALUES (?, ?, ?, ?)
                    """,
                    (document_id, query_text, response_text, agent_type)
                )
                return cursor.lastrowid
        except Exception as e:
            logging.error(f"Error saving query: {e}")
            raise

    def delete_query(self, query_id: int) -> bool:
        """Delete a query from the database"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "DELETE FROM queries WHERE id = ?",
                    (query_id,)
                )
                return cursor.rowcount > 0
        except Exception as e:
            logging.error(f"Error deleting query: {e}")
            raise

    def get_recent_queries(self, document_id: Optional[int] = None, limit: int = 5) -> list:
        """Retrieve recent queries for a document or all recent queries"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                if document_id:
                    cursor.execute(
                        """
                        SELECT id, query_text, response_text, agent_type, created_at
                        FROM queries WHERE document_id = ?
                        ORDER BY created_at DESC LIMIT ?
                        """,
                        (document_id, limit)
                    )
                else:
                    cursor.execute(
                        """
                        SELECT id, query_text, response_text, agent_type, created_at
                        FROM queries ORDER BY created_at DESC LIMIT ?
                        """,
                        (limit,)
                    )
                return cursor.fetchall()
        except Exception as e:
            logging.error(f"Error retrieving queries: {e}")
            raise

    def get_recent_documents(self, limit: int = 5) -> list:
        """Retrieve recently accessed documents"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    SELECT id, filename, file_type, upload_date, last_accessed
                    FROM documents ORDER BY last_accessed DESC LIMIT ?
                    """,
                    (limit,)
                )
                return cursor.fetchall()
        except Exception as e:
            logging.error(f"Error retrieving recent documents: {e}")
            raise

    def delete_document(self, document_id: int) -> bool:
        """Delete a document and all related records from the database"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                # Delete related records first
                cursor.execute("DELETE FROM document_analysis WHERE document_id = ?", (document_id,))
                cursor.execute("DELETE FROM queries WHERE document_id = ?", (document_id,))
                # Delete the document
                cursor.execute("DELETE FROM documents WHERE id = ?", (document_id,))
                return cursor.rowcount > 0
        except Exception as e:
            logging.error(f"Error deleting document: {e}")
            raise
