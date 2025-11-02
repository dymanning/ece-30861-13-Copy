from flask import Flask, request, jsonify

app = Flask(__name__)

# Dummy in-memory store
artifacts = {}

@app.route("/upload", methods=["POST"])
def upload():
    file = request.files.get("file")
    if not file:
        return jsonify({"error": "No file provided"}), 400
    # save file or just store name
    artifacts[file.filename] = "stored"
    return jsonify({"message": f"{file.filename} uploaded successfully"}), 200

@app.route("/artifacts", methods=["GET"])
def get_artifacts():
    return jsonify({"artifacts": list(artifacts.keys())})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=80)
