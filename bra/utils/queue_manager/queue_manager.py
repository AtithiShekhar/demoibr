"""
utils/queue_manager/queue_manager.py
Queue-based job processing system for handling multiple analysis requests
Updated for centralized scoring system
"""

import queue
import threading
import uuid
import time
import json
import os
import shutil
from datetime import datetime
from typing import Dict, Optional,List
from pathlib import Path
from utils.response_formatter import format_complete_response

def collect_results_detailed(results_dir: str, workspace_dir: str) -> Dict:
    """
    Collect and format results with FULL analysis details
    
    Args:
        results_dir: Path to results directory
        workspace_dir: Path to workspace directory
        
    Returns:
        Dictionary with formatted results including all analysis details
    """
    from utils.response_formatter import format_complete_response
    
    raw_results = []
    aggregated_rmm_table = []
    consequences_data = {}
    
    if not os.path.exists(results_dir):
        return None
    
    # Collect primary results (skip ALT_ files - they'll be linked later)
    for filename in sorted(os.listdir(results_dir)):
        if filename.startswith("ALT_") or filename.startswith("analysis_summary_"):
            continue
            
        if filename.endswith(".json"):
            file_path = os.path.join(results_dir, filename)
            
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                
                # Extract ALL analysis details
                analyses = data.get("analyses", {})
                summary = analyses.get("summary", {})
                brr_data = data.get("benefit_risk_ratio", {})
                
                # Parse filename to extract drug and condition
                base_name = filename.replace("_result.json", "")
                parts = base_name.split("_")
                
                if len(parts) >= 2:
                    medicine_name = parts[0]
                    condition = "_".join(parts[1:]).replace("_", " ")
                else:
                    medicine_name = "Unknown"
                    condition = "Unknown"
                
                # Collect RMM data
                med_rmm = summary.get("rmm", [])
                if isinstance(med_rmm, list):
                    aggregated_rmm_table.extend(med_rmm)
                
                # Collect consequences data
                med_consequence = summary.get("consequence", {})
                if med_consequence and "factor_2_6_consequences_of_non_treatment" in med_consequence:
                    consequences_data.update(med_consequence["factor_2_6_consequences_of_non_treatment"])
                
                # Collect alternative results for this primary drug
                alt_results = collect_alternatives_for_drug(
                    results_dir, 
                    medicine_name, 
                    condition
                )
                
                # Build comprehensive primary result
                primary_result = {
                    "success": True,
                    "drug": medicine_name,
                    "diagnosis": condition,
                    "total_benefit_score": brr_data.get("total_benefit_score", 0),
                    "total_risk_score": brr_data.get("total_risk_score", 0),
                    "brr": brr_data.get("brr"),
                    "brr_interpretation": brr_data.get("interpretation"),
                    "rct_count": summary.get("rct_count", 0),
                    "has_contraindication": summary.get("has_contraindication", False),
                    "has_life_threatening_adrs": summary.get("has_life_threatening_adrs", False),
                    "has_serious_adrs": summary.get("has_serious_adrs", False),
                    "has_drug_interactions": summary.get("has_drug_interactions", False),
                    "duplication_checked": summary.get("therapeutic_duplication_performed", False),
                    "alternatives_count": len(alt_results),
                    "alternative_analyses": alt_results,
                    "output_file": file_path  # Pass file path for detailed extraction
                    ,"rmf":summary.get("rmf")
                }
                
                raw_results.append(primary_result)
            
            except Exception as e:
                print(f"⚠ Error reading {filename}: {e}")
                import traceback
                traceback.print_exc()
                continue
    
    # Format complete response with all details
    return format_complete_response(
        raw_results, 
        rmm_table=aggregated_rmm_table,
        consequences_data=consequences_data
    )


def collect_alternatives_for_drug(results_dir: str, drug_name: str, condition: str) -> List[Dict]:
    """
    Collect all alternative analyses for a specific primary drug
    
    Args:
        results_dir: Results directory path
        drug_name: Primary drug name
        condition: Condition being treated
        
    Returns:
        List of alternative analysis results
    """
    alt_results = []
    
    for alt_file in sorted(os.listdir(results_dir)):
        if not alt_file.startswith("ALT_") or not alt_file.endswith("_result.json"):
            continue
        
        try:
            alt_path = os.path.join(results_dir, alt_file)
            with open(alt_path, "r") as af:
                alt_data = json.load(af)
            
            alt_analyses = alt_data.get("analyses", {})
            alt_summary = alt_analyses.get("summary", {})
            alt_brr = alt_data.get("benefit_risk_ratio", {})
            
            # Extract alt drug name from filename: ALT_DRUGNAME_Condition_result.json
            alt_base = alt_file.replace("ALT_", "").replace("_result.json", "")
            alt_parts = alt_base.split("_")
            alt_drug_name = alt_parts[0] if alt_parts else "Unknown"
            
            # Extract condition from filename
            alt_condition = "_".join(alt_parts[1:]).replace("_", " ") if len(alt_parts) > 1 else ""
            
            # Only include if this alternative is for the current primary drug's condition
            if alt_condition.lower() == condition.lower():
                alt_results.append({
                    "success": True,
                    "drug": alt_drug_name,
                    "diagnosis": condition,
                    "total_benefit_score": alt_brr.get("total_benefit_score", 0),
                    "total_risk_score": alt_brr.get("total_risk_score", 0),
                    "brr": alt_brr.get("brr"),
                    "brr_interpretation": alt_brr.get("interpretation"),
                    "rct_count": alt_summary.get("rct_count", 0),
                    "has_contraindication": alt_summary.get("has_contraindication", False),
                    "has_life_threatening_adrs": alt_summary.get("has_life_threatening_adrs", False),
                    "has_serious_adrs": alt_summary.get("has_serious_adrs", False),
                    "has_drug_interactions": alt_summary.get("has_drug_interactions", False),
                    "alternative_info": {
                        "brand_name": alt_drug_name,
                        "generic_name": alt_drug_name,
                        "alternative_rank": len(alt_results) + 1,
                        "primary_drug": drug_name,
                        "primary_diagnosis": condition
                    },
                    "output_file": alt_path  # Pass file path for detailed extraction
                })
        
        except Exception as e:
            print(f"Error reading alternative {alt_file}: {e}")
            continue
    
    return alt_results



class AnalysisJob:
    """Represents a single analysis job"""
    
    def __init__(self, job_id: str, request_data: dict):
        self.job_id = job_id
        self.request_data = request_data
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
        self.num_workers = int(os.getenv("NUM_WORKERS", "2"))
        self.running = False
        
        # Create base results directory if it doesn't exist
        os.makedirs("results", exist_ok=True)
        
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
        
        print(f"✓ Started {self.num_workers} worker threads")
    
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
        print("✓ All workers stopped")
    
    def submit_job(self, request_data: dict) -> str:
        """
        Submit a new analysis job to the queue
        
        Args:
            request_data: Request data dictionary (EMR format)
            
        Returns:
            job_id: Unique job identifier
        """
        job_id = str(uuid.uuid4())
        job = AnalysisJob(job_id, request_data)
        
        with self.jobs_lock:
            self.jobs[job_id] = job
        
        self.job_queue.put(job_id)
        
        patient_name = request_data.get('patientInfo', {}).get('fullName', 'Unknown')
        print(f"✓ Job {job_id[:8]}... submitted for {patient_name} (Queue: {self.job_queue.qsize()})")
        
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
                "input": job.request_data
            }
            
            if job.status == "completed":
                status_dict["result"] = job.result
            elif job.status == "failed":
                status_dict["error"] = job.error
            
            return status_dict
    
    def _get_queue_position(self, job_id: str) -> int:
        """Get position of job in queue (approximate)"""
        return self.job_queue.qsize()
    
    def _worker(self):
        """Worker thread that processes jobs from the queue"""
        thread_name = threading.current_thread().name
        print(f"✓ {thread_name} started")
        
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
                print(f"✗ {thread_name} error: {e}")
                import traceback
                traceback.print_exc()
        
        print(f"✓ {thread_name} stopped")
    
    def _process_job(self, job: AnalysisJob, worker_name: str):
        """
        Process a single job using the new main() function
        
        Args:
            job: AnalysisJob object
            worker_name: Name of worker thread
        """
        job_id_short = job.job_id[:8]
        patient_name = job.request_data.get('patientInfo', {}).get('fullName', 'Unknown')
        
        print(f"\n[{worker_name}] Processing job {job_id_short}... ({patient_name})")
        
        # Update job status
        with self.jobs_lock:
            job.status = "processing"
            job.started_at = datetime.now()
        
        # Create job-specific workspace
        job_workspace = f"workspace_{job.job_id}"
        input_file = os.path.join(job_workspace, "input.json")
        results_dir = os.path.join(job_workspace, "results")
        
        try:
            # Create workspace
            os.makedirs(job_workspace, exist_ok=True)
            os.makedirs(results_dir, exist_ok=True)
            
            # Write input file
            with open(input_file, "w", encoding="utf-8") as f:
                json.dump(job.request_data, f, indent=2)
            
            # Import main function
            from main import main as run_analysis
            
            # Change to job workspace
            original_dir = os.getcwd()
            os.chdir(job_workspace)
            
            # Run analysis
            start_time = time.perf_counter()
            success = run_analysis(
                verbose=False,
                input_file="input.json",
                output_summary=True
            )
            end_time = time.perf_counter()
            execution_time = end_time - start_time
            
            # Return to original directory
            os.chdir(original_dir)
            
            # Collect results
            results = self._collect_results(results_dir, job_workspace)
            
            # Update job with results
            with self.jobs_lock:
                if success and results:
                    job.status = "completed"
                    job.result = results
                    job.execution_time = round(execution_time, 2)
                    print(f"✓ [{worker_name}] Job {job_id_short}... completed in {execution_time:.2f}s")
                else:
                    job.status = "failed"
                    job.error = "Analysis failed or no results generated"
                    print(f"✗ [{worker_name}] Job {job_id_short}... failed")
                
                job.completed_at = datetime.now()
        
        except Exception as e:
            print(f"✗ [{worker_name}] Error processing job {job_id_short}...: {e}")
            import traceback
            traceback.print_exc()
            
            with self.jobs_lock:
                job.status = "failed"
                job.error = f"{str(e)}\n{traceback.format_exc()}"
                job.completed_at = datetime.now()
        
        finally:
            # Cleanup job workspace
            try:
                if os.path.exists(job_workspace):
                    shutil.rmtree(job_workspace)
            except Exception as e:
                print(f"⚠ Cleanup error for job {job_id_short}...: {e}")
    
    # Inside your JobQueue class in the main orchestration file
    def _collect_results(self, results_dir: str, workspace_dir: str) -> Dict:
      '''Wrapper method for JobQueue class'''
      return collect_results_detailed(results_dir, workspace_dir)
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
    
    def clear_completed_jobs(self, max_age_hours: int = 24):
        """
        Clear completed/failed jobs older than specified hours
        
        Args:
            max_age_hours: Maximum age in hours for keeping jobs
        """
        current_time = datetime.now()
        jobs_to_remove = []
        
        with self.jobs_lock:
            for job_id, job in self.jobs.items():
                if job.status in ["completed", "failed"] and job.completed_at:
                    age_hours = (current_time - job.completed_at).total_seconds() / 3600
                    if age_hours > max_age_hours:
                        jobs_to_remove.append(job_id)
            
            for job_id in jobs_to_remove:
                del self.jobs[job_id]
        
        if jobs_to_remove:
            print(f"✓ Cleared {len(jobs_to_remove)} old jobs")
        
        return len(jobs_to_remove)


# Global queue instance
job_queue = JobQueue()
