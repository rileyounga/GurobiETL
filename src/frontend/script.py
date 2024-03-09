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
    # 'data' is an 'ImmutableMultiDict'. See the following documentation:
    # https://tedboy.github.io/flask/generated/generated/werkzeug.ImmutableMultiDict.html
    # we can convert it to a Python dictionary using the to_dict() method.
    data = request.form
    data_dict = data.to_dict()
    print("Got input:", data_dict)

    # request.files is an ImmutableMultiDict of files found in the request.
    # Each file is tied to a key named 'file'.
    # If we upload three files, there will be three distinct keys named 'file'.
    # The getlist('file') method constructs a list of all files, each
    # represented using the FileStorage class:
    # https://tedboy.github.io/flask/generated/generated/werkzeug.FileStorage.html
    files = request.files.getlist('file')
    print("Got files:", [file.filename for file in files])
    #files[0].save(files[0].filename) # can save files, too
    
    return jsonify(data)

if __name__ == '__main__':
    app.run(debug=True, port=8080)