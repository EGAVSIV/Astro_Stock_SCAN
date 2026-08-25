from flask import Flask, jsonify, send_from_directory
from flask_cors import CORS
import run_scanner
import os

app = Flask(__name__, static_folder=".")
CORS(app)

@app.route("/")
def serve_index():
    return send_from_directory(".", "index.html")

@app.route("/<path:path>")
def serve_static(path):
    return send_from_directory(".", path)

@app.route("/api/run-scan", methods=["POST"])
def trigger_scan():
    try:
        run_scanner.run_pipeline()
        return jsonify({"status": "success", "message": "Data successfully updated!"}), 200
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

if __name__ == "__main__":
    print("Starting AstroScan Local Workflow Server at http://localhost:5000")
    app.run(port=5000, debug=True)
