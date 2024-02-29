import numpy as np
import pandas as pd
import gurobipy as gp
import argparse
from gurobipy import GRB
from flask import Flask, request, jsonify
from flask_cors import CORS

"""
Context:
#fetch path: src/app/problem/page.js
#cur path: src/api/script.py
"""

app = Flask(__name__)
CORS(app)
CORS(app, resources={r"/api/*": {"origins": "http://localhost:3000"}})


@app.route('/api/home', methods=['POST'])
def home():
    data = request.get_json()
    # split the data by json keys
    problemType = data["problemType"]
    variables = data["variables"]
    objective = data["objective"]
    constraints = data["constraints"]
    files = data["files"]
    # try loading one of the files
    try:
        data = pd.read_csv(files[0])
    except:
        pass
    return jsonify(data)

if __name__ == '__main__':
    app.run(debug=True, port=8080)