"""
utils/queue_manager/queue_manager_with_database.py
Queue-based job processing system with PostgreSQL integration
Saves completed analyses to database asynchronously
"""

import queue
import threading
import uuid
import time
import json
import os
import shutil
from datetime import datetime
from typing import Dict, Optional, List
from pathlib import Path


def collect_results_with_ibr_scoring(results_dir: str, workspace_dir: str, input_data: Dict) -> Dict:
    """
    Collect results and add all new scoring components for iBR Report
    
    Args:
        results_dir: Path to results directory
        workspace_dir: Path to workspace directory
        input_data: Original input EMR data
        
    Returns:
        Dictionary with complete iBR Report
    """
    from utils.response_formatter import format_complete_response
    from utils.ibr_report_generator import format_ibr_response
    from scoring.config import ScoringConfig
    
    raw_results = []
    aggregated_rmm_table = []
    consequences_data = {}
    
    if not os.path.exists(results_dir):
        return None
    
    # Collect primary results
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
                
                # Parse filename
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
                
                # Collect RMF data
                rmf_data = summary.get("rmf", {})
                
                # Calculate new scores
                consequence_score = None
                if consequences_data:
                    consequence_score = ScoringConfig.calculate_consequences_score(consequences_data)
                
                lt_adr_score = None
                lt_adrs_data = analyses.get("adrs", {}).get("life_threatening_adrs_data", {})
                if lt_adrs_data:
                    lt_adr_score = ScoringConfig.calculate_lt_adr_score(lt_adrs_data)
                
                serious_adr_score = None
                serious_adrs_data = analyses.get("adrs", {}).get("serious_adrs_data", {})
                if serious_adrs_data:
                    serious_adr_score = ScoringConfig.calculate_serious_adr_score(serious_adrs_data)
                
                interaction_score = None
                interactions_data = analyses.get("adrs", {}).get("interactions_data", {})
                if interactions_data:
                    interaction_score = ScoringConfig.calculate_drug_interaction_score(interactions_data)
                
                rmf_score = None
                if rmf_data:
                    rmf_score = ScoringConfig.calculate_mitigation_feasibility_score(rmf_data)
                
                # Collect alternatives
                alt_results = collect_alternatives_for_drug(results_dir, medicine_name, condition)
                
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
                    "output_file": file_path,
                    "rmf_data": rmf_data,
                    "consequence_score": consequence_score,
                    "lt_adr_score": lt_adr_score,
                    "serious_adr_score": serious_adr_score,
                    "interaction_score": interaction_score,
                    "rmf_score": rmf_score,
                    "rmm_data": med_rmm,
                    "consequence_data": med_consequence
                }
                
                raw_results.append(primary_result)
            
            except Exception as e:
                print(f"⚠ Error reading {filename}: {e}")
                import traceback
                traceback.print_exc()
                continue
    
    # Format complete response
    formatted_response = format_complete_response(
        raw_results, 
        rmm_table=aggregated_rmm_table,
        consequences_data=consequences_data
    )
    
    # Generate iBR Report
    ibr_report = format_ibr_response(formatted_response, input_data)
    formatted_response["ibr_report"] = ibr_report
    
    # Add scoring summary
    formatted_response["scoring_summary"] = {
        "total_consequence_benefit": sum(
            r.get("consequence_score", {}).get("weighted_score", 0) 
            for r in raw_results if r.get("consequence_score")
        ),
        "total_lt_adr_risk": sum(
            r.get("lt_adr_score", {}).get("weighted_score", 0) 
            for r in raw_results if r.get("lt_adr_score")
        ),
        "total_serious_adr_risk": sum(
            r.get("serious_adr_score", {}).get("weighted_score", 0) 
            for r in raw_results if r.get("serious_adr_score")
        ),
        "total_interaction_risk": sum(
            r.get("interaction_score", {}).get("weighted_score", 0) 
            for r in raw_results if r.get("interaction_score")
        ),
        "total_rmf_risk": sum(
            r.get("rmf_score", {}).get("weighted_score", 0) 
            for r in raw_results if r.get("rmf_score")
        )
    }
    
    return formatted_response


def collect_alternatives_for_drug(results_dir: str, drug_name: str, condition: str) -> List[Dict]:
    """Collect all alternative analyses for a specific primary drug"""
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
            
            alt_base = alt_file.replace("ALT_", "").replace("_result.json", "")
            alt_parts = alt_base.split("_")
            alt_drug_name = alt_parts[0] if alt_parts else "Unknown"
            alt_condition = "_".join(alt_parts[1:]).replace("_", " ") if len(alt_parts) > 1 else ""
            
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
                    "output_file": alt_path
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
    """Queue manager with PostgreSQL integration"""
    
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
        self.jobs = {}
        self.jobs_lock = threading.Lock()
        self.workers = []
        self.num_workers = int(os.getenv("NUM_WORKERS", "2"))
        self.running = False
        
        # Initialize database handler
        try:
            from utils.database.db_handler import db_handler
            self.db_handler = db_handler
            self.db_enabled = True
            print("✓ Database integration enabled")
        except Exception as e:
            print(f"⚠ Database integration disabled: {e}")
            self.db_handler = None
            self.db_enabled = False
        
        os.makedirs("results", exist_ok=True)
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
        for _ in range(self.num_workers):
            self.job_queue.put(None)
        for worker in self.workers:
            worker.join(timeout=5)
        self.workers = []
        
        if self.db_enabled and self.db_handler:
            self.db_handler.stop_worker()
        
        print("✓ All workers stopped")
    
    def submit_job(self, request_data: dict) -> str:
        """Submit a new analysis job"""
        job_id = str(uuid.uuid4())
        job = AnalysisJob(job_id, request_data)
        
        with self.jobs_lock:
            self.jobs[job_id] = job
        
        # Save to database (async)
        if self.db_enabled:
            self.db_handler.save_analysis_async(job_id, self._job_to_dict(job))
        
        self.job_queue.put(job_id)
        
        patient_name = request_data.get('patientInfo', {}).get('fullName', 'Unknown')
        print(f"✓ Job {job_id[:8]}... submitted for {patient_name}")
        
        return job_id
    
    def get_job_status(self, job_id: str) -> Optional[Dict]:
        """
        Get job status - first check memory, then database
        
        Args:
            job_id: Unique job identifier
            
        Returns:
            Dictionary with job status and result (if completed)
        """
        # First check in-memory jobs
        with self.jobs_lock:
            job = self.jobs.get(job_id)
            
            if job:
                status_dict = {
                    "job_id": job.job_id,
                    "status": job.status,
                    "created_at": job.created_at.isoformat(),
                    "started_at": job.started_at.isoformat() if job.started_at else None,
                    "completed_at": job.completed_at.isoformat() if job.completed_at else None,
                    "execution_time": job.execution_time,
                    "queue_position": self._get_queue_position(job_id) if job.status == "queued" else None,
                }
                
                if job.status == "completed":
                    status_dict["result"] = job.result
                elif job.status == "failed":
                    status_dict["error"] = job.error
                
                return status_dict
        
        # If not in memory, try database
        if self.db_enabled:
            db_result = self.db_handler.get_analysis_by_job_id(job_id)
            if db_result:
                return {
                    "job_id": db_result['job_id'],
                    "status": db_result['status'],
                    "created_at": db_result['created_at'],
                    "started_at": db_result['started_at'],
                    "completed_at": db_result['completed_at'],
                    "execution_time": db_result['execution_time'],
                    "result": db_result.get('result_data'),
                    "error": db_result.get('error_message'),
                    "source": "database"
                }
        
        return None
    
    def _get_queue_position(self, job_id: str) -> int:
        """Get position of job in queue"""
        return self.job_queue.qsize()
    
    def _job_to_dict(self, job: AnalysisJob) -> Dict:
        """Convert job object to dictionary"""
        return {
            "job_id": job.job_id,
            "status": job.status,
            "created_at": job.created_at.isoformat(),
            "started_at": job.started_at.isoformat() if job.started_at else None,
            "completed_at": job.completed_at.isoformat() if job.completed_at else None,
            "execution_time": job.execution_time,
            "input": job.request_data,
            "result": job.result,
            "error": job.error
        }
    
    def _worker(self):
        """Worker thread that processes jobs"""
        thread_name = threading.current_thread().name
        print(f"✓ {thread_name} started")
        
        while self.running:
            try:
                job_id = self.job_queue.get(timeout=1)
                
                if job_id is None:
                    break
                
                with self.jobs_lock:
                    job = self.jobs.get(job_id)
                
                if not job:
                    continue
                
                self._process_job(job, thread_name)
                self.job_queue.task_done()
                
            except queue.Empty:
                continue
            except Exception as e:
                print(f"✗ {thread_name} error: {e}")
                import traceback
                traceback.print_exc()
        
        print(f"✓ {thread_name} stopped")
    
    def _process_job(self, job: AnalysisJob, worker_name: str):
        """Process a single job with database integration"""
        job_id_short = job.job_id[:8]
        patient_name = job.request_data.get('patientInfo', {}).get('fullName', 'Unknown')
        
        print(f"\n[{worker_name}] Processing job {job_id_short}... ({patient_name})")
        
        with self.jobs_lock:
            job.status = "processing"
            job.started_at = datetime.now()
        
        # Update database status (async)
        if self.db_enabled:
            self.db_handler.update_job_status_async(
                job.job_id,
                "processing",
                started_at=job.started_at.isoformat()
            )
        
        job_workspace = f"workspace_{job.job_id}"
        input_file = os.path.join(job_workspace, "input.json")
        results_dir = os.path.join(job_workspace, "results")
        
        try:
            os.makedirs(job_workspace, exist_ok=True)
            os.makedirs(results_dir, exist_ok=True)
            
            with open(input_file, "w", encoding="utf-8") as f:
                json.dump(job.request_data, f, indent=2)
            
            from main import main as run_analysis
            
            original_dir = os.getcwd()
            os.chdir(job_workspace)
            
            start_time = time.perf_counter()
            success = run_analysis(
                verbose=False,
                input_file="input.json",
                output_summary=True
            )
            end_time = time.perf_counter()
            execution_time = end_time - start_time
            
            os.chdir(original_dir)
            
            # Collect results
            results = collect_results_with_ibr_scoring(results_dir, job_workspace, job.request_data)
            
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
            
            # Save complete result to database (async)
            if self.db_enabled:
                self.db_handler.save_analysis_async(job.job_id, self._job_to_dict(job))
        
        except Exception as e:
            print(f"✗ [{worker_name}] Error processing job {job_id_short}...: {e}")
            import traceback
            traceback.print_exc()
            
            with self.jobs_lock:
                job.status = "failed"
                job.error = f"{str(e)}\n{traceback.format_exc()}"
                job.completed_at = datetime.now()
            
            # Save error to database (async)
            if self.db_enabled:
                self.db_handler.save_analysis_async(job.job_id, self._job_to_dict(job))
        
        finally:
            try:
                if os.path.exists(job_workspace):
                    shutil.rmtree(job_workspace)
            except Exception as e:
                print(f"⚠ Cleanup error for job {job_id_short}...: {e}")
    
    def get_queue_stats(self) -> Dict:
        """Get queue and database statistics"""
        with self.jobs_lock:
            total_jobs = len(self.jobs)
            queued = sum(1 for j in self.jobs.values() if j.status == "queued")
            processing = sum(1 for j in self.jobs.values() if j.status == "processing")
            completed = sum(1 for j in self.jobs.values() if j.status == "completed")
            failed = sum(1 for j in self.jobs.values() if j.status == "failed")
        
        stats = {
            "memory": {
                "total_jobs": total_jobs,
                "queued": queued,
                "processing": processing,
                "completed": completed,
                "failed": failed,
                "queue_size": self.job_queue.qsize(),
                "active_workers": self.num_workers
            }
        }
        
        # Add database stats if enabled
        if self.db_enabled:
            db_stats = self.db_handler.get_database_stats()
            stats["database"] = db_stats
        
        return stats
    
    def clear_completed_jobs(self, max_age_hours: int = 24):
        """Clear completed/failed jobs from memory and database"""
        current_time = datetime.now()
        jobs_to_remove = []
        
        # Clear from memory
        with self.jobs_lock:
            for job_id, job in self.jobs.items():
                if job.status in ["completed", "failed"] and job.completed_at:
                    age_hours = (current_time - job.completed_at).total_seconds() / 3600
                    if age_hours > max_age_hours:
                        jobs_to_remove.append(job_id)
            
            for job_id in jobs_to_remove:
                del self.jobs[job_id]
        
        if jobs_to_remove:
            print(f"✓ Cleared {len(jobs_to_remove)} old jobs from memory")
        
        # Note: Database cleanup handled separately via cleanup endpoint
        return len(jobs_to_remove)


# Global queue instance
job_queue = JobQueue()