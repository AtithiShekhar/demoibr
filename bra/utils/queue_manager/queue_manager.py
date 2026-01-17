"""
utils/queue_manager.py
Queue-based job processing system for handling multiple analysis requests
"""

import queue
import threading
import uuid
import time
import json
import os
from datetime import datetime
from typing import Dict, Optional
from main import main as run_analysis


class AnalysisJob:
    """Represents a single analysis job"""
    
    def __init__(self, job_id: str, request_data: dict):
        self.job_id = job_id
        self.request_data = request_data   # 👈 already input.json content
        self.status = "queued"
        self.created_at = datetime.now()
        self.started_at = None
        self.completed_at = None
        self.result = None
        self.error = None
        self.execution_time = None


class JobQueue:
    """Singleton queue manager for analysis jobs"""
    
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
        self.job_queue = queue.Queue()
        self.jobs = {}  # job_id -> AnalysisJob
        self.jobs_lock = threading.Lock()
        self.workers = []
        self.num_workers = 2  # Number of concurrent workers
        self.running = False
        
        # Start worker threads
        self.start_workers()
    
    def start_workers(self):
        """Start background worker threads"""
        if self.running:
            return
        
        self.running = True
        for i in range(self.num_workers):
            worker = threading.Thread(
                target=self._worker,
                name=f"AnalysisWorker-{i+1}",
                daemon=True
            )
            worker.start()
            self.workers.append(worker)
        
        print(f"Started {self.num_workers} worker threads")
    
    def stop_workers(self):
        """Stop all worker threads"""
        self.running = False
        
        # Add sentinel values to stop workers
        for _ in range(self.num_workers):
            self.job_queue.put(None)
        
        # Wait for workers to finish
        for worker in self.workers:
            worker.join(timeout=5)
        
        self.workers = []
        print("All workers stopped")
    
    def submit_job(self, request_data: dict) -> str:
        """
        Submit a new analysis job to the queue
        
        Args:
            request_data: Request data dictionary
            
        Returns:
            job_id: Unique job identifier
        """
        job_id = str(uuid.uuid4())
        job = AnalysisJob(job_id, request_data)
        
        with self.jobs_lock:
            self.jobs[job_id] = job
        
        self.job_queue.put(job_id)
        print(f"Job {job_id} submitted to queue (Queue size: {self.job_queue.qsize()})")
        
        return job_id
    
    def get_job_status(self, job_id: str) -> Optional[Dict]:
        """
        Get status of a job
        
        Args:
            job_id: Job identifier
            
        Returns:
            Dictionary with job status or None if not found
        """
        with self.jobs_lock:
            job = self.jobs.get(job_id)
            
            if not job:
                return None
            
            status_dict = {
    "job_id": job.job_id,
    "status": job.status,
    "created_at": job.created_at.isoformat(),
    "started_at": job.started_at.isoformat() if job.started_at else None,
    "completed_at": job.completed_at.isoformat() if job.completed_at else None,
    "execution_time": job.execution_time,
    "queue_position": self._get_queue_position(job_id) if job.status == "queued" else None,
    "input": job.request_data   # 👈 input.json content
}
            
            if job.status == "completed":
                status_dict["result"] = job.result
            elif job.status == "failed":
                status_dict["error"] = job.error
            
            return status_dict
    
    def _get_queue_position(self, job_id: str) -> int:
        """Get position of job in queue (approximate)"""
        # This is approximate since queue doesn't support indexing
        return self.job_queue.qsize()
    
    def _worker(self):
        """Worker thread that processes jobs from the queue"""
        thread_name = threading.current_thread().name
        print(f"{thread_name} started")
        
        while self.running:
            try:
                # Get job from queue (blocking with timeout)
                job_id = self.job_queue.get(timeout=1)
                
                # Check for sentinel value
                if job_id is None:
                    break
                
                # Get job object
                with self.jobs_lock:
                    job = self.jobs.get(job_id)
                
                if not job:
                    continue
                
                # Process the job
                self._process_job(job, thread_name)
                
                # Mark task as done
                self.job_queue.task_done()
                
            except queue.Empty:
                continue
            except Exception as e:
                print(f"{thread_name} error: {e}")
        
        print(f"{thread_name} stopped")
    
    def _process_job(self, job: AnalysisJob, worker_name: str):
        """
        Process a single job
        
        Args:
            job: AnalysisJob object
            worker_name: Name of worker thread
        """
        print(f"{worker_name} processing job {job.job_id}")
        
        # Update job status
        with self.jobs_lock:
            job.status = "processing"
            job.started_at = datetime.now()
        
        # Create temporary input file for this job
        input_file = f"input_{job.job_id}.json"
        results_dir = f"results_{job.job_id}"
        
        try:
            # Write input file
            with open(input_file, "w", encoding="utf-8") as f:
                json.dump(job.request_data, f, indent=2)
            
            # Create results directory
            os.makedirs(results_dir, exist_ok=True)
            
            # Temporarily change working directory context
            original_input = "input.json"
            original_results = "results"
            
            # Symlink or rename for main() to use
            if os.path.exists(original_input):
                os.rename(original_input, f"{original_input}.bak_{job.job_id}")
            if os.path.exists(original_results):
                os.rename(original_results, f"{original_results}.bak_{job.job_id}")
            
            os.rename(input_file, original_input)
            os.rename(results_dir, original_results)
            
            # Run analysis
            start_time = time.perf_counter()
            success = run_analysis(verbose=False)
            end_time = time.perf_counter()
            execution_time = end_time - start_time
            
            # Collect results
            results = self._collect_results()
            
            # Restore original files
            os.rename(original_input, input_file)
            os.rename(original_results, results_dir)
            
            if os.path.exists(f"{original_input}.bak_{job.job_id}"):
                os.rename(f"{original_input}.bak_{job.job_id}", original_input)
            if os.path.exists(f"{original_results}.bak_{job.job_id}"):
                os.rename(f"{original_results}.bak_{job.job_id}", original_results)
            
            # Update job with results
            with self.jobs_lock:
                if success:
                    job.status = "completed"
                    job.result = results
                    job.execution_time = round(execution_time, 2)
                else:
                    job.status = "failed"
                    job.error = "Analysis failed"
                
                job.completed_at = datetime.now()
            
            print(f"{worker_name} completed job {job.job_id} in {execution_time:.2f}s")
        
        except Exception as e:
            print(f"{worker_name} error processing job {job.job_id}: {e}")
            
            with self.jobs_lock:
                job.status = "failed"
                job.error = str(e)
                job.completed_at = datetime.now()
        
        finally:
            # Cleanup temporary files
            self._cleanup_job_files(job.job_id, input_file, results_dir)
    
    def _collect_results(self) -> Dict:
        """Collect results from results directory"""
        results_payload = []
        results_dir = "results"
        
        if os.path.exists(results_dir):
            for filename in sorted(os.listdir(results_dir)):
                if filename.endswith(".json"):
                    file_path = os.path.join(results_dir, filename)
                    
                    try:
                        with open(file_path, "r", encoding="utf-8") as f:
                            data = json.load(f)
                        
                        parts = filename.replace("_result.json", "").split("_")
                        medicine_name = parts[0] if len(parts) > 0 else "Unknown"
                        condition = "_".join(parts[1:]) if len(parts) > 1 else "Unknown"
                        
                        results_payload.append({
                            "medicine_name": medicine_name,
                            "condition": condition,
                            "result": data
                        })
                    
                    except Exception as e:
                        print(f"Error reading {filename}: {e}")
                        continue
        
        return {
            "result_count": len(results_payload),
            "results": results_payload
        }
    
    def _cleanup_job_files(self, job_id: str, input_file: str, results_dir: str):
        """Clean up temporary job files"""
        try:
            if os.path.exists(input_file):
                os.remove(input_file)
            
            if os.path.exists(results_dir):
                import shutil
                shutil.rmtree(results_dir)
        
        except Exception as e:
            print(f"Cleanup error for job {job_id}: {e}")
    
    def get_queue_stats(self) -> Dict:
        """Get statistics about the queue"""
        with self.jobs_lock:
            total_jobs = len(self.jobs)
            queued = sum(1 for j in self.jobs.values() if j.status == "queued")
            processing = sum(1 for j in self.jobs.values() if j.status == "processing")
            completed = sum(1 for j in self.jobs.values() if j.status == "completed")
            failed = sum(1 for j in self.jobs.values() if j.status == "failed")
        
        return {
            "total_jobs": total_jobs,
            "queued": queued,
            "processing": processing,
            "completed": completed,
            "failed": failed,
            "queue_size": self.job_queue.qsize(),
            "active_workers": self.num_workers
        }


# Global queue instance
job_queue = JobQueue()