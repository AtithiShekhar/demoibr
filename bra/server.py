from flask import Flask, request, jsonify
import os
import json
import shutil

from main import main  # your godfather function

app = Flask(__name__)

INPUT_FILE = "input.json"
RESULTS_DIR = "results"


@app.route("/analyze", methods=["POST"])
def analyze():


    if not request.is_json:
        return jsonify({"error": "Request body must be JSON"}), 400

    request_data = request.get_json()


    with open(INPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(request_data, f, indent=2)

    try:
       
        success = main()
        if not success:
            return jsonify({"error": "Analysis failed"}), 500

        response_payload = []

        # 4️⃣ Read all result files
        if os.path.exists(RESULTS_DIR):
            for filename in sorted(os.listdir(RESULTS_DIR)):
                if filename.endswith(".json"):
                    file_path = os.path.join(RESULTS_DIR, filename)
                    with open(file_path, "r", encoding="utf-8") as f:
                        data = json.load(f)

                    response_payload.append({
                        "medicine_name": filename.split('_')[0],
                        "condition": filename.split('_')[1],
                        "result": data
                    })

        # 5️⃣ Build response
        response = {
            "status": "completed",
            "result_count": len(response_payload),
            "results": response_payload
        }

        return jsonify(response)

    finally:
        # 6️⃣ Cleanup (ALWAYS runs)

        # Delete input.json
        if os.path.exists(INPUT_FILE):
            os.remove(INPUT_FILE)

        # Flush results directory
        if os.path.exists(RESULTS_DIR):
            shutil.rmtree(RESULTS_DIR)
            os.makedirs(RESULTS_DIR, exist_ok=True)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000, debug=True)