"""
server.py
Flask API server with queue-based job processing
Keeps main thread free for handling concurrent requests
"""

from flask import Flask, request, jsonify
import os
from utils.queue_manager.queue_manager import job_queue

app = Flask(__name__)


@app.route("/analyze", methods=["POST"])
def analyze():
    """
    Submit an analysis job to the queue (non-blocking)
    
    Returns immediately with job_id for status polling
    
    Expected JSON input:
    {
        "patient": {...},
        "prescription": [...]
    }
    
    Returns:
    {
        "status": "accepted",
        "job_id": "uuid",
        "message": "Job queued for processing",
        "poll_url": "/status/<job_id>"
    }
    """
    
    # Validate request
    if not request.is_json:
        return jsonify({"error": "Request body must be JSON"}), 400
    
    request_data = request.get_json()
    
    # Validate required fields
    if "patient" not in request_data:
        return jsonify({"error": "Missing 'patient' field in request"}), 400
    
    if "prescription" not in request_data or not request_data["prescription"]:
        return jsonify({"error": "Missing or empty 'prescription' field"}), 400
    
    # Submit job to queue
    try:
        job_id = job_queue.submit_job(request_data)
        
        return jsonify({
            "status": "accepted",
            "job_id": job_id,
            "message": "Job queued for processing",
            "poll_url": f"/status/{job_id}",
            "queue_stats": job_queue.get_queue_stats()
        }), 202  # 202 Accepted
    
    except Exception as e:
        return jsonify({
            "error": f"Failed to submit job: {str(e)}"
        }), 500


@app.route("/status/<job_id>", methods=["GET"])
def get_status(job_id):
    """
    Get status of a specific job
    
    Returns:
    - If queued: {"status": "queued", "queue_position": 3}
    - If processing: {"status": "processing", "started_at": "..."}
    - If completed: {"status": "completed", "result": {...}}
    - If failed: {"status": "failed", "error": "..."}
    """
    
    job_status = job_queue.get_job_status(job_id)
    
    if not job_status:
        return jsonify({
            "error": "Job not found",
            "job_id": job_id
        }), 404
    
    return jsonify(job_status), 200


@app.route("/analyze/sync", methods=["POST"])
def analyze_sync():
    """
    Synchronous analysis endpoint (blocks until complete)
    
    Use this for immediate results, but server can only handle one at a time
    Use /analyze (async) for concurrent requests
    """
    
    # Validate request
    if not request.is_json:
        return jsonify({"error": "Request body must be JSON"}), 400
    
    request_data = request.get_json()
    
    # Validate required fields
    if "patient" not in request_data:
        return jsonify({"error": "Missing 'patient' field in request"}), 400
    
    if "prescription" not in request_data or not request_data["prescription"]:
        return jsonify({"error": "Missing or empty 'prescription' field"}), 400
    
    # Submit job and wait for completion
    try:
        job_id = job_queue.submit_job(request_data)
        
        # Poll for completion (blocking)
        import time
        max_wait = 600  # 10 minutes timeout
        start_time = time.time()
        
        while time.time() - start_time < max_wait:
            job_status = job_queue.get_job_status(job_id)
            
            if job_status["status"] == "completed":
                return jsonify({
                    "status": "completed",
                    "job_id": job_id,
                    "execution_time": job_status["execution_time"],
                    **job_status["result"]
                }), 200
            
            elif job_status["status"] == "failed":
                return jsonify({
                    "status": "failed",
                    "job_id": job_id,
                    "error": job_status["error"]
                }), 500
            
            # Wait before next poll
            time.sleep(2)
        
        # Timeout
        return jsonify({
            "error": "Request timeout",
            "job_id": job_id,
            "message": "Job is still processing. Use /status/<job_id> to check status"
        }), 504
    
    except Exception as e:
        return jsonify({
            "error": f"Analysis error: {str(e)}"
        }), 500


@app.route("/queue/stats", methods=["GET"])
def queue_stats():
    """Get queue statistics"""
    stats = job_queue.get_queue_stats()
    return jsonify(stats), 200


@app.route("/health", methods=["GET"])
def health():
    """Health check endpoint"""
    stats = job_queue.get_queue_stats()
    return jsonify({
        "status": "healthy",
        "service": "Drug Analysis API",
        "version": "2.0.0",
        "queue_enabled": True,
        "queue_stats": stats
    }), 200


@app.route("/", methods=["GET"])
def index():
    """API information endpoint"""
    return jsonify({
        "service": "Drug Analysis API (Queue-Based)",
        "version": "2.0.0",
        "endpoints": {
            "/analyze": "POST - Submit async analysis job (recommended)",
            "/analyze/sync": "POST - Submit sync analysis (blocks until complete)",
            "/status/<job_id>": "GET - Get job status",
            "/queue/stats": "GET - Get queue statistics",
            "/health": "GET - Health check",
            "/": "GET - API information"
        },
        "workflow": {
            "async": [
                "1. POST /analyze -> Get job_id",
                "2. Poll GET /status/<job_id> until completed",
                "3. Retrieve results from status response"
            ],
            "sync": [
                "1. POST /analyze/sync -> Wait for results",
                "2. Get results immediately (blocks)"
            ]
        },
        "example_request": {
            "patient": {
                "age": 60,
                "gender": "Male",
                "diagnosis": "fever",
                "condition": "headache",
                "date_of_assessment": "2026-01-06"
            },
            "prescription": ["acetaminophen", "amoxicillin"],
            "PubMed": {"email": "your_email@example.com"}
        }
    }), 200


@app.errorhandler(404)
def not_found(error):
    """Handle 404 errors"""
    return jsonify({"error": "Endpoint not found"}), 404


@app.errorhandler(500)
def internal_error(error):
    """Handle 500 errors"""
    return jsonify({"error": "Internal server error"}), 500


if __name__ == "__main__":
    print("="*80)
    print("Drug Analysis API Server (Queue-Based)")
    print("="*80)
    print("Starting server on http://0.0.0.0:8000")
    print("\nEndpoints:")
    print("  POST /analyze       - Submit async job (non-blocking)")
    print("  POST /analyze/sync  - Submit sync job (blocking)")
    print("  GET  /status/<id>   - Check job status")
    print("  GET  /queue/stats   - Queue statistics")
    print("  GET  /health        - Health check")
    print("  GET  /              - API info")
    print("\nQueue Workers: 2 (configurable)")
    print("="*80)
    
    try:
        app.run(host="0.0.0.0", port=8000, debug=False, threaded=True)
    finally:
        # Cleanup on shutdown
        job_queue.stop_workers()