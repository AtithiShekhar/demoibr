"""
utils/database/db_handler.py
Async PostgreSQL database handler for analysis results
Non-blocking database operations using threading
"""

import psycopg2
from psycopg2.extras import Json, RealDictCursor
import threading
import queue
import os
from datetime import datetime
from typing import Dict, Optional, List
import json
from contextlib import contextmanager


class DatabaseHandler:
    """Async database handler with connection pooling"""
    
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        
        self._initialized = True
        
        # Database configuration from environment
        self.db_config = {
            'host': os.getenv('DB_HOST', 'localhost'),
            'port': int(os.getenv('DB_PORT', '5432')),
            'database': os.getenv('DB_NAME', 'drug_analysis'),
            'user': os.getenv('DB_USER', 'drug_api_user'),
            'password': os.getenv('DB_PASSWORD', ''),
        }
        
        # Queue for async operations
        self.operation_queue = queue.Queue()
        self.running = False
        self.worker_thread = None
        
        # Connection pool (simple implementation)
        self.connections = []
        self.pool_size = 5
        self.connections_lock = threading.Lock()
        
        # Initialize connection pool
        self._init_pool()
        
        # Start background worker
        self.start_worker()
        
        print(f"✓ Database handler initialized (Host: {self.db_config['host']}, DB: {self.db_config['database']})")
    
    def _init_pool(self):
        """Initialize connection pool"""
        try:
            for _ in range(self.pool_size):
                conn = psycopg2.connect(**self.db_config)
                self.connections.append(conn)
            print(f"✓ Connection pool initialized ({self.pool_size} connections)")
        except Exception as e:
            print(f"✗ Failed to initialize connection pool: {e}")
            raise
    
    @contextmanager
    def get_connection(self):
        """Get a connection from the pool (context manager)"""
        conn = None
        try:
            with self.connections_lock:
                if self.connections:
                    conn = self.connections.pop()
                else:
                    # Create new connection if pool is empty
                    conn = psycopg2.connect(**self.db_config)
            
            yield conn
            
        except Exception as e:
            if conn:
                conn.rollback()
            raise e
        finally:
            if conn:
                with self.connections_lock:
                    # Return connection to pool
                    if len(self.connections) < self.pool_size:
                        self.connections.append(conn)
                    else:
                        conn.close()
    
    def start_worker(self):
        """Start background worker thread for async operations"""
        if self.running:
            return
        
        self.running = True
        self.worker_thread = threading.Thread(
            target=self._worker,
            name="DatabaseWorker",
            daemon=True
        )
        self.worker_thread.start()
        print("✓ Database worker thread started")
    
    def stop_worker(self):
        """Stop background worker thread"""
        self.running = False
        self.operation_queue.put(None)  # Signal to stop
        if self.worker_thread:
            self.worker_thread.join(timeout=5)
        
        # Close all connections
        with self.connections_lock:
            for conn in self.connections:
                conn.close()
            self.connections.clear()
        
        print("✓ Database worker thread stopped")
    
    def _worker(self):
        """Background worker that processes database operations"""
        print("✓ DatabaseWorker started")
        
        while self.running:
            try:
                operation = self.operation_queue.get(timeout=1)
                
                if operation is None:
                    break
                
                func, args, kwargs = operation
                try:
                    func(*args, **kwargs)
                except Exception as e:
                    print(f"✗ Database operation error: {e}")
                    import traceback
                    traceback.print_exc()
                
                self.operation_queue.task_done()
                
            except queue.Empty:
                continue
            except Exception as e:
                print(f"✗ DatabaseWorker error: {e}")
        
        print("✓ DatabaseWorker stopped")
    
    def _queue_operation(self, func, *args, **kwargs):
        """Queue a database operation for async execution"""
        self.operation_queue.put((func, args, kwargs))
    
    # ========================================================================
    # ASYNC OPERATIONS (Non-blocking)
    # ========================================================================
    
    def save_analysis_async(self, job_id: str, job_data: Dict):
        """
        Save analysis result asynchronously (non-blocking)
        
        Args:
            job_id: Unique job identifier
            job_data: Complete job data including status, input, result
        """
        self._queue_operation(self._save_analysis_sync, job_id, job_data)
    
    def update_job_status_async(self, job_id: str, status: str, **kwargs):
        """
        Update job status asynchronously
        
        Args:
            job_id: Unique job identifier
            status: New status (queued, processing, completed, failed)
            **kwargs: Additional fields to update (started_at, completed_at, etc.)
        """
        self._queue_operation(self._update_job_status_sync, job_id, status, **kwargs)
    
    # ========================================================================
    # SYNC OPERATIONS (Blocking - called by worker thread)
    # ========================================================================
    
    def _save_analysis_sync(self, job_id: str, job_data: Dict):
        """Save analysis result to database (called by worker thread)"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                # Extract patient info
                input_data = job_data.get('input', {})
                patient_info = input_data.get('patientInfo', {})
                
                # Extract result summary
                result = job_data.get('result')
                error = job_data.get('error')
                
                # Count medications and diagnoses
                num_medications = 0
                num_diagnoses = len(input_data.get('currentDiagnoses', []))
                
                for diagnosis in input_data.get('currentDiagnoses', []):
                    meds = diagnosis.get('treatment', {}).get('medications', [])
                    num_medications += len(meds)
                
                # Check for critical alerts
                has_critical = False
                has_warnings = False
                
                if result:
                    alerts = result.get('alerts', {})
                    has_critical = bool(alerts.get('critical'))
                    has_warnings = bool(alerts.get('warnings'))
                
                # Insert main record
                cursor.execute("""
                    INSERT INTO analysis_results (
                        job_id, patient_name, patient_mrn, patient_age, patient_gender,
                        status, created_at, started_at, completed_at, execution_time,
                        input_data, result_data, error_message,
                        num_medications, num_diagnoses, has_critical_alerts, has_warnings
                    ) VALUES (
                        %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
                    )
                    ON CONFLICT (job_id) DO UPDATE SET
                        status = EXCLUDED.status,
                        started_at = EXCLUDED.started_at,
                        completed_at = EXCLUDED.completed_at,
                        execution_time = EXCLUDED.execution_time,
                        result_data = EXCLUDED.result_data,
                        error_message = EXCLUDED.error_message,
                        has_critical_alerts = EXCLUDED.has_critical_alerts,
                        has_warnings = EXCLUDED.has_warnings
                """, (
                    job_id,
                    patient_info.get('fullName'),
                    patient_info.get('mrn'),
                    patient_info.get('age'),
                    patient_info.get('gender'),
                    job_data.get('status', 'unknown'),
                    datetime.fromisoformat(job_data['created_at']),
                    datetime.fromisoformat(job_data['started_at']) if job_data.get('started_at') else None,
                    datetime.fromisoformat(job_data['completed_at']) if job_data.get('completed_at') else None,
                    job_data.get('execution_time'),
                    Json(input_data),
                    Json(result) if result else None,
                    error,
                    num_medications,
                    num_diagnoses,
                    has_critical,
                    has_warnings
                ))
                
                # Insert medication analyses
                if result and 'medication_analysis' in result:
                    for med_analysis in result['medication_analysis']:
                        medication = med_analysis.get('medication', {})
                        
                        cursor.execute("""
                            INSERT INTO medication_analyses (
                                job_id, medication_name, diagnosis,
                                brr_score, safety_outcome,
                                has_contraindication, has_lt_adrs, has_serious_adrs
                            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                            ON CONFLICT DO NOTHING
                        """, (
                            job_id,
                            medication.get('medication_name'),
                            medication.get('indication'),
                            float(medication.get('benefit_risk_score', {}).get('ratio_value', 0)),
                            medication.get('safety_profile', {}).get('outcome'),
                            medication.get('contraindication_analysis', {}).get('contraindication_found', False),
                            False,  # has_lt_adrs - extract from result
                            False   # has_serious_adrs - extract from result
                        ))
                
                conn.commit()
                print(f"✓ Saved analysis for job {job_id[:8]}... to database")
                
        except Exception as e:
            print(f"✗ Error saving analysis {job_id[:8]}...: {e}")
            import traceback
            traceback.print_exc()
    
    def _update_job_status_sync(self, job_id: str, status: str, **kwargs):
        """Update job status in database (called by worker thread)"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                # Build dynamic UPDATE query
                update_fields = ['status = %s']
                params = [status]
                
                if 'started_at' in kwargs and kwargs['started_at']:
                    update_fields.append('started_at = %s')
                    params.append(datetime.fromisoformat(kwargs['started_at']))
                
                if 'completed_at' in kwargs and kwargs['completed_at']:
                    update_fields.append('completed_at = %s')
                    params.append(datetime.fromisoformat(kwargs['completed_at']))
                
                if 'execution_time' in kwargs:
                    update_fields.append('execution_time = %s')
                    params.append(kwargs['execution_time'])
                
                if 'error_message' in kwargs:
                    update_fields.append('error_message = %s')
                    params.append(kwargs['error_message'])
                
                params.append(job_id)
                
                query = f"""
                    UPDATE analysis_results 
                    SET {', '.join(update_fields)}
                    WHERE job_id = %s
                """
                
                cursor.execute(query, params)
                conn.commit()
                
        except Exception as e:
            print(f"✗ Error updating job status {job_id[:8]}...: {e}")
    
    # ========================================================================
    # QUERY OPERATIONS (Sync - for API endpoints)
    # ========================================================================
    
    def get_analysis_by_job_id(self, job_id: str) -> Optional[Dict]:
        """
        Get analysis result by job_id (blocking)
        
        Args:
            job_id: Unique job identifier
            
        Returns:
            Dictionary with analysis data or None if not found
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor(cursor_factory=RealDictCursor)
                
                cursor.execute("""
                    SELECT 
                        job_id, status, created_at, started_at, completed_at,
                        execution_time, patient_name, patient_mrn, patient_age, patient_gender,
                        input_data, result_data, error_message,
                        num_medications, num_diagnoses, has_critical_alerts, has_warnings
                    FROM analysis_results
                    WHERE job_id = %s
                """, (job_id,))
                
                result = cursor.fetchone()
                
                if result:
                    # Convert to dict and format timestamps
                    data = dict(result)
                    
                    # Format timestamps
                    if data.get('created_at'):
                        data['created_at'] = data['created_at'].isoformat()
                    if data.get('started_at'):
                        data['started_at'] = data['started_at'].isoformat()
                    if data.get('completed_at'):
                        data['completed_at'] = data['completed_at'].isoformat()
                    
                    # Convert Decimal to float
                    if data.get('execution_time'):
                        data['execution_time'] = float(data['execution_time'])
                    
                    return data
                
                return None
                
        except Exception as e:
            print(f"✗ Error fetching job {job_id[:8]}...: {e}")
            return None
    
    def get_recent_analyses(self, limit: int = 10, status: str = None) -> List[Dict]:
        """
        Get recent analyses
        
        Args:
            limit: Maximum number of results
            status: Filter by status (optional)
            
        Returns:
            List of analysis records
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor(cursor_factory=RealDictCursor)
                
                if status:
                    cursor.execute("""
                        SELECT job_id, status, created_at, completed_at, execution_time,
                               patient_name, patient_mrn, num_medications, num_diagnoses,
                               has_critical_alerts, has_warnings
                        FROM analysis_results
                        WHERE status = %s
                        ORDER BY created_at DESC
                        LIMIT %s
                    """, (status, limit))
                else:
                    cursor.execute("""
                        SELECT job_id, status, created_at, completed_at, execution_time,
                               patient_name, patient_mrn, num_medications, num_diagnoses,
                               has_critical_alerts, has_warnings
                        FROM analysis_results
                        ORDER BY created_at DESC
                        LIMIT %s
                    """, (limit,))
                
                results = cursor.fetchall()
                
                # Format timestamps
                formatted_results = []
                for row in results:
                    data = dict(row)
                    if data.get('created_at'):
                        data['created_at'] = data['created_at'].isoformat()
                    if data.get('completed_at'):
                        data['completed_at'] = data['completed_at'].isoformat()
                    if data.get('execution_time'):
                        data['execution_time'] = float(data['execution_time'])
                    formatted_results.append(data)
                
                return formatted_results
                
        except Exception as e:
            print(f"✗ Error fetching recent analyses: {e}")
            return []
    
    def get_database_stats(self) -> Dict:
        """Get database statistics"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor(cursor_factory=RealDictCursor)
                
                cursor.execute("SELECT * FROM analysis_stats")
                stats = cursor.fetchone()
                
                if stats:
                    result = dict(stats)
                    # Convert Decimal to float
                    for key in ['avg_execution_time', 'max_execution_time', 'min_execution_time']:
                        if result.get(key):
                            result[key] = float(result[key])
                    return result
                
                return {}
                
        except Exception as e:
            print(f"✗ Error fetching database stats: {e}")
            return {}
    
    def cleanup_old_jobs(self, days: int = 30) -> int:
        """
        Delete jobs older than specified days
        
        Args:
            days: Delete jobs older than this many days
            
        Returns:
            Number of jobs deleted
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                cursor.execute("""
                    DELETE FROM analysis_results
                    WHERE created_at < NOW() - INTERVAL '%s days'
                    AND status IN ('completed', 'failed')
                """, (days,))
                
                deleted_count = cursor.rowcount
                conn.commit()
                
                print(f"✓ Deleted {deleted_count} old jobs")
                return deleted_count
                
        except Exception as e:
            print(f"✗ Error cleaning up old jobs: {e}")
            return 0


# Global database handler instance
db_handler = DatabaseHandler()