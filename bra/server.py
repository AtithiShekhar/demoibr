"""
server.py - UPDATED WITH DATABASE INTEGRATION
Flask API server with PostgreSQL backend
Non-blocking database operations
"""

from flask import Flask, request, jsonify
import os
import time
from utils.queue_manager.queue_manager import job_queue

app = Flask(__name__)

import json
from datetime import datetime


def simplify_medical_data(complex_data):
    """Simplifies EMR data while preserving full MedicalHistory array"""
    patient_info = complex_data.get("patientInfo", {})
    
    current_diagnoses = [d.get("diagnosisName") for d in complex_data.get("currentDiagnoses", [])]
    complaints_list = [c.get("complaint") for c in complex_data.get("chiefComplaints", [])]
    medical_history_array = complex_data.get("MedicalHistory", [])
    
    medication_names = set()
    
    for dx in complex_data.get("currentDiagnoses", []):
        meds = dx.get("treatment", {}).get("medications", [])
        for med in meds:
            if med.get("name"):
                medication_names.add(med["name"])
                
    for h_dx in medical_history_array:
        h_meds = h_dx.get("treatment", {}).get("medications", [])
        for h_med in h_meds:
            if h_med.get("name"):
                medication_names.add(h_med["name"])
    
    simplified = {
        "patient": {
            "age": patient_info.get("age"),
            "gender": patient_info.get("gender"),
            "condition": ", ".join(complaints_list),
            "diagnosis": ", ".join(current_diagnoses),
            "social_risk_factors": patient_info.get('social_risk_factors'), 
            "date_of_assessment": datetime.now().strftime("%Y-%m-%d"),
            "MedicalHistory": medical_history_array 
        },
        "prescription": list(medication_names)
    }
    
    return simplified


@app.route("/analyze", methods=["POST"])
def analyze():
    """
    Submit an analysis job to the queue (non-blocking)
    Returns immediately with job_id for status polling
    """
    if not request.is_json:
        return jsonify({"error": "Request body must be JSON"}), 400
    
    request_data = request.get_json()
    
    # Validate required fields
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
    
    # Save simplified input
    with open("adrs_input.json",'w') as f:
        json.dump(simplify_medical_data(request_data), f, indent=2)
    
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
    """
    Get status of a specific job
    Checks memory first, then database
    """
    job_status = job_queue.get_job_status(job_id)
    
    if not job_status:
        return jsonify({"error": "Job not found", "job_id": job_id}), 404
    
    # Add data source info
    if job_status.get("source") == "database":
        job_status["note"] = "Retrieved from database (analysis completed earlier)"
    
    return jsonify(job_status), 200


@app.route("/queue/stats", methods=["GET"])
def queue_stats():
    """Get queue and database statistics"""
    return jsonify(job_queue.get_queue_stats()), 200


@app.route("/queue/cleanup", methods=["POST"])
def queue_cleanup():
    """Clean up old completed jobs from memory"""
    max_age = request.json.get("max_age_hours", 24) if request.is_json else 24
    removed = job_queue.clear_completed_jobs(max_age)
    return jsonify({"removed_jobs": removed, "max_age_hours": max_age}), 200


@app.route("/database/cleanup", methods=["POST"])
def database_cleanup():
    """
    Clean up old jobs from database
    Removes completed/failed jobs older than specified days
    """
    days = request.json.get("days", 30) if request.is_json else 30
    
    try:
        from utils.database.db_handler import db_handler
        removed = db_handler.cleanup_old_jobs(days)
        return jsonify({
            "status": "success",
            "removed_jobs": removed,
            "days": days
        }), 200
    except Exception as e:
        return jsonify({
            "status": "error",
            "error": str(e)
        }), 500


@app.route("/database/stats", methods=["GET"])
def database_stats():
    """Get database statistics"""
    try:
        from utils.database.db_handler import db_handler
        stats = db_handler.get_database_stats()
        return jsonify(stats), 200
    except Exception as e:
        return jsonify({
            "error": str(e)
        }), 500


@app.route("/database/recent", methods=["GET"])
def recent_analyses():
    """
    Get recent analyses from database
    Query parameters:
    - limit: Number of results (default: 10)
    - status: Filter by status (optional)
    """
    limit = int(request.args.get('limit', 10))
    status = request.args.get('status')
    
    try:
        from utils.database.db_handler import db_handler
        results = db_handler.get_recent_analyses(limit=limit, status=status)
        return jsonify({
            "count": len(results),
            "results": results
        }), 200
    except Exception as e:
        return jsonify({
            "error": str(e)
        }), 500


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
    """Health check with database status"""
    health_data = {
        "status": "healthy",
        "service": "Drug Analysis API",
        "version": "2.0.0",
        "scoring_system": "Centralized Configuration",
        "queue_stats": job_queue.get_queue_stats()
    }
    
    # Check database connectivity
    try:
        from utils.database.db_handler import db_handler
        db_stats = db_handler.get_database_stats()
        health_data["database"] = {
            "status": "connected",
            "total_analyses": db_stats.get("total_analyses", 0)
        }
    except Exception as e:
        health_data["database"] = {
            "status": "disconnected",
            "error": str(e)
        }
    
    return jsonify(health_data), 200


@app.route("/", methods=["GET"])
def index():
    """API information"""
    return jsonify({
        "service": "Drug Analysis API",
        "version": "2.0.0",
        "scoring_system": "Centralized Configuration",
        "database": "PostgreSQL",
        "endpoints": {
            "/analyze": "POST - Submit async job",
            "/status/<job_id>": "GET - Get job status (checks memory & database)",
            "/queue/stats": "GET - Queue statistics",
            "/queue/cleanup": "POST - Clean old jobs from memory",
            "/database/stats": "GET - Database statistics",
            "/database/recent": "GET - Recent analyses from database",
            "/database/cleanup": "POST - Clean old jobs from database",
            "/scoring/config": "GET - View scoring matrices",
            "/health": "GET - Health check"
        },
        "features": [
            "Centralized scoring configuration",
            "Parallel analysis execution",
            "PostgreSQL database persistence",
            "Async database operations (non-blocking)",
            "Therapeutic duplication detection",
            "Alternative medication finder",
            "Queue-based job processing",
            "iBR Report generation"
        ]
    }), 200


if __name__ == "__main__":
    print("="*80)
    print("Drug Analysis API Server v2.0")
    print("With PostgreSQL Database Integration")
    print("="*80)
    print(f"Server: http://0.0.0.0:8000")
    print(f"Workers: {job_queue.num_workers}")
    print(f"Database: {'Enabled' if job_queue.db_enabled else 'Disabled'}")
    print("="*80)
    
    try:
        app.run(host="0.0.0.0", port=8000, debug=False, threaded=True)
    finally:
        job_queue.stop_workers()