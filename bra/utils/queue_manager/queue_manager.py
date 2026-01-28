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
from typing import Dict, Optional
from pathlib import Path


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
    
    def _collect_results(self, results_dir: str, workspace_dir: str) -> Dict:
        """
        Collect and format results from results directory
        Uses worker results directly since alternatives are already attached
        
        Args:
            results_dir: Path to results directory
            workspace_dir: Path to workspace directory
            
        Returns:
            Dictionary with formatted results (clean, concise)
        """
        from utils.response_formatter import format_complete_response
        import json
        import os
        
        raw_results = []
        
        if not os.path.exists(results_dir):
            return None
        
        # Collect individual result files - SKIP alternatives (they start with ALT_)
        for filename in sorted(os.listdir(results_dir)):
            # Skip alternative files - they'll be collected with their primary
            if filename.startswith("ALT_") or filename.startswith("analysis_summary_"):
                continue
                
            if filename.endswith(".json"):
                file_path = os.path.join(results_dir, filename)
                
                try:
                    with open(file_path, "r", encoding="utf-8") as f:
                        data = json.load(f)
                    
                    # Parse filename to extract drug and condition
                    base_name = filename.replace("_result.json", "")
                    parts = base_name.split("_")
                    
                    if len(parts) >= 2:
                        medicine_name = parts[0]
                        condition = "_".join(parts[1:]).replace("_", " ")
                    else:
                        medicine_name = "Unknown"
                        condition = "Unknown"
                    
                    # Extract key data from analyses
                    analyses = data.get("analyses", {})
                    summary = analyses.get("summary", {})
                    brr_data = data.get("benefit_risk_ratio", {})
                    
                    # Now look for ALT_ files for this primary drug
                    alt_results = []
                    for alt_file in os.listdir(results_dir):
                        # Match pattern: ALT_DrugName_Condition_result.json
                        if alt_file.startswith("ALT_") and alt_file.endswith("_result.json"):
                            try:
                                alt_path = os.path.join(results_dir, alt_file)
                                with open(alt_path, "r") as af:
                                    alt_data = json.load(af)
                                
                                alt_summary = alt_data.get("analyses", {}).get("summary", {})
                                alt_brr = alt_data.get("benefit_risk_ratio", {})
                                
                                # Extract alt drug name from filename
                                # Format: ALT_DRUGNAME_Condition_result.json
                                alt_base = alt_file.replace("ALT_", "").replace("_result.json", "")
                                alt_parts = alt_base.split("_")
                                alt_drug_name = alt_parts[0] if alt_parts else "Unknown"
                                
                                # Check if this alternative belongs to current primary
                                # by comparing the condition names
                                alt_condition = "_".join(alt_parts[1:]).replace("_", " ") if len(alt_parts) > 1 else ""
                                
                                if alt_condition == condition:
                                    alt_results.append({
                                        "success": True,
                                        "drug": alt_drug_name,
                                        "total_benefit_score": alt_brr.get("total_benefit_score", 0),
                                        "total_risk_score": alt_brr.get("total_risk_score", 0),
                                        "brr": alt_brr.get("brr"),
                                        "brr_interpretation": alt_brr.get("interpretation"),
                                        "rct_count": alt_summary.get("rct_count", 0),
                                        "has_contraindication": alt_summary.get("has_contraindication", False),
                                        "alternative_info": {
                                            "brand_name": alt_drug_name,
                                            "generic_name": alt_drug_name,
                                            "alternative_rank": len(alt_results) + 1,
                                            "primary_drug": medicine_name,
                                            "primary_diagnosis": condition
                                        }
                                    })
                            except Exception as e:
                                print(f"Error reading alternative {alt_file}: {e}")
                    
                    # Build primary result with alternatives attached
                    raw_results.append({
                        "success": True,
                        "drug": medicine_name,
                        "diagnosis": condition,
                        "total_benefit_score": brr_data.get("total_benefit_score", 0),
                        "total_risk_score": brr_data.get("total_risk_score", 0),
                        "brr": brr_data.get("brr"),
                        "brr_interpretation": brr_data.get("interpretation"),
                        "rct_count": summary.get("rct_count", 0),
                        "has_contraindication": summary.get("has_contraindication", False),
                        "duplication_checked": summary.get("therapeutic_duplication_performed", False),
                        "alternatives_count": len(alt_results),
                        "alternative_analyses": alt_results
                    })
                
                except Exception as e:
                    print(f"⚠ Error reading {filename}: {e}")
                    import traceback
                    traceback.print_exc()
                    continue
        
        # Format response using clean formatter
        return format_complete_response(raw_results)
    
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


# ================================
# server.py (COMPLETE VERSION)
# ================================

"""
server.py
Flask API server with queue-based job processing
Updated for centralized scoring system v2.0
"""

from flask import Flask, request, jsonify
import os
import time

app = Flask(__name__)


@app.route("/analyze", methods=["POST"])
def analyze():
    """
    Submit an analysis job to the queue (non-blocking)
    Returns immediately with job_id for status polling
    """
    if not request.is_json:
        return jsonify({"error": "Request body must be JSON"}), 400
    
    request_data = request.get_json()
    
    # Validate required fields for NEW EMR schema
    if "patientInfo" not in request_data:
        return jsonify({"error": "Missing 'patientInfo' field"}), 400
    
    if "currentDiagnoses" not in request_data or not request_data["currentDiagnoses"]:
        return jsonify({"error": "Missing or empty 'currentDiagnoses' field"}), 400
    
    # Validate at least one diagnosis has medications
    has_medications = False
    for diagnosis in request_data["currentDiagnoses"]:
        meds = diagnosis.get("treatment", {}).get("medications", [])
        if meds:
            has_medications = True
            break
    
    if not has_medications:
        return jsonify({"error": "No medications found in any diagnosis"}), 400
    
    # Submit job to queue
    try:
        job_id = job_queue.submit_job(request_data)
        
        return jsonify({
            "status": "accepted",
            "job_id": job_id,
            "message": "Job queued for processing",
            "poll_url": f"/status/{job_id}",
            "queue_stats": job_queue.get_queue_stats()
        }), 202
    
    except Exception as e:
        return jsonify({"error": f"Failed to submit job: {str(e)}"}), 500


@app.route("/status/<job_id>", methods=["GET"])
def get_status(job_id):
    """Get status of a specific job"""
    job_status = job_queue.get_job_status(job_id)
    
    if not job_status:
        return jsonify({"error": "Job not found", "job_id": job_id}), 404
    
    return jsonify(job_status), 200


@app.route("/analyze/sync", methods=["POST"])
def analyze_sync():
    """Synchronous analysis endpoint (blocks until complete)"""
    if not request.is_json:
        return jsonify({"error": "Request body must be JSON"}), 400
    
    request_data = request.get_json()
    
    # Validate
    if "patientInfo" not in request_data:
        return jsonify({"error": "Missing 'patientInfo' field"}), 400
    
    if "currentDiagnoses" not in request_data or not request_data["currentDiagnoses"]:
        return jsonify({"error": "Missing or empty 'currentDiagnoses' field"}), 400
    
    try:
        job_id = job_queue.submit_job(request_data)
        
        # Poll for completion
        max_wait = 600  # 10 minutes
        start_time = time.time()
        poll_interval = 2
        
        while time.time() - start_time < max_wait:
            job_status = job_queue.get_job_status(job_id)
            
            if job_status["status"] == "completed":
                return jsonify({
                    "status": "completed",
                    "job_id": job_id,
                    "execution_time": job_status["execution_time"],
                    "result": job_status["result"]
                }), 200
            
            elif job_status["status"] == "failed":
                return jsonify({
                    "status": "failed",
                    "job_id": job_id,
                    "error": job_status["error"]
                }), 500
            
            time.sleep(poll_interval)
        
        return jsonify({
            "error": "Request timeout",
            "job_id": job_id,
            "message": f"Job still processing after {max_wait}s. Use /status/{job_id}"
        }), 504
    
    except Exception as e:
        return jsonify({"error": f"Analysis error: {str(e)}"}), 500


@app.route("/queue/stats", methods=["GET"])
def queue_stats():
    """Get queue statistics"""
    return jsonify(job_queue.get_queue_stats()), 200


@app.route("/queue/cleanup", methods=["POST"])
def queue_cleanup():
    """Clean up old completed jobs"""
    max_age = request.json.get("max_age_hours", 24) if request.is_json else 24
    removed = job_queue.clear_completed_jobs(max_age)
    return jsonify({"removed_jobs": removed, "max_age_hours": max_age}), 200


@app.route("/scoring/config", methods=["GET"])
def scoring_config():
    """Get current scoring configuration"""
    from scoring.config import ScoringConfig
    
    config_data = {
        "version": "2.0",
        "benefit_factors": {
            "indication_strength": {
                key: {
                    "description": entry.description,
                    "weight": entry.weight,
                    "score": entry.score,
                    "weighted_score": entry.weighted_score
                }
                for key, entry in ScoringConfig.INDICATION_STRENGTH.items()
            },
            "evidence_strength": {
                key: {
                    "description": entry.description,
                    "weight": entry.weight,
                    "score": entry.score,
                    "weighted_score": entry.weighted_score
                }
                for key, entry in ScoringConfig.EVIDENCE_STRENGTH.items()
            }
        },
        "risk_factors": {
            "contraindication": {
                key: {
                    "description": entry.description,
                    "weight": entry.weight,
                    "score": entry.score,
                    "weighted_score": entry.weighted_score
                }
                for key, entry in ScoringConfig.CONTRAINDICATION.items()
            }
        }
    }
    
    return jsonify(config_data), 200


@app.route("/health", methods=["GET"])
def health():
    """Health check"""
    return jsonify({
        "status": "healthy",
        "service": "Drug Analysis API",
        "version": "2.0.0",
        "scoring_system": "Centralized Configuration",
        "queue_stats": job_queue.get_queue_stats()
    }), 200


@app.route("/", methods=["GET"])
def index():
    """API information"""
    return jsonify({
        "service": "Drug Analysis API",
        "version": "2.0.0",
        "scoring_system": "Centralized Configuration",
        "endpoints": {
            "/analyze": "POST - Submit async job",
            "/analyze/sync": "POST - Submit sync job",
            "/status/<job_id>": "GET - Get job status",
            "/queue/stats": "GET - Queue statistics",
            "/queue/cleanup": "POST - Clean old jobs",
            "/scoring/config": "GET - View scoring matrices",
            "/health": "GET - Health check"
        },
        "features": [
            "Centralized scoring configuration",
            "Parallel analysis execution",
            "Therapeutic duplication detection",
            "Alternative medication finder",
            "Queue-based job processing"
        ]
    }), 200


if __name__ == "__main__":
    print("="*80)
    print("Drug Analysis API Server v2.0")
    print("Centralized Scoring System")
    print("="*80)
    print(f"Server: http://0.0.0.0:8000")
    print(f"Workers: {job_queue.num_workers}")
    print("="*80)
    
    try:
        app.run(host="0.0.0.0", port=8000, debug=False, threaded=True)
    finally:
        job_queue.stop_workers()