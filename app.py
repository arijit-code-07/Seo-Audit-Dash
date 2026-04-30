#!/usr/bin/env python3
"""Flask API for SEO Audit Tool"""

from flask import Flask, request, jsonify, render_template_string
from flask_cors import CORS
import asyncio
import json
import os
import sys

# Add parent dir to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from seo_auditor import SEOAuditor

app = Flask(__name__)
CORS(app)

# Global auditor instance (initialized on first request)
auditor = None

async def get_auditor():
    global auditor
    if auditor is None:
        auditor = SEOAuditor()
        await auditor.init()
    return auditor

@app.route('/')
def index():
    return render_template_string(open('dashboard.html').read())

@app.route('/api/audit', methods=['POST'])
def audit():
    data = request.get_json()
    url = data.get('url')

    if not url:
        return jsonify({"error": "URL is required"}), 400

    try:
        async def run_audit():
            aud = await get_auditor()
            result = await aud.audit(url)
            return aud.result_to_dict(result)

        result = asyncio.run(run_audit())
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/health')
def health():
    return jsonify({"status": "ok"})

if __name__ == '__main__':
    print("Starting SEO Audit API server...")
    print("Open http://localhost:5000 in your browser")
    app.run(host='0.0.0.0', port=5000, debug=False)
