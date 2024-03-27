import re
import numpy as np
import pandas as pd
import gurobipy as gp
from gurobipy import GRB
from flask import Flask, request, jsonify
from flask_cors import CORS
import re
import json
from utils import parse_data, parse

"""
Context:
#fetch path: src/app/problem/page.js
#cur path: src/api/script.py
"""

app = Flask(__name__)
CORS(app)
CORS(app, resources={r"/api/*": {"origins": "http://localhost:3000"}})
verbose=False


@app.route('/api/home', methods=['POST'])
def home():
    # 'data' is an 'ImmutableMultiDict'. See the following documentation:
    # https://tedboy.github.io/flask/generated/generated/werkzeug.ImmutableMultiDict.html
    data = request.form
    data_dict = {key: json.loads(value) for (key, value) in zip(data.keys(), data.values())}
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

    """
    needed input:
    files = ["costs.csv", "coverage.csv", "population.csv"]
    data_dict = {"parameters": {"budget": 20},
                 "variables": ["build_Tower", "iscovered_Region"], 
                 "objective": ["sum(iscovered_Region * Population_Region)", "maximize"], 
                 "constraints": ["sum(build_Tower * Cost_Tower) <= budget"]}
    
    @Thomas sorry to change up the form again, but I think I have a better grasp of the
    desired user input now.

    Working off of this modelling example:
    https://github.com/Gurobi/modeling-examples/blob/master/cell_tower_coverage/cell_tower.ipynb
    """
    # Parse the data
    df_dict = parse_data(files)
    # @Zhangpeng This dictionary of dataframes can now be fed into the visualization module
    # Since I am first trying out a coverage problem, an arc node graph might be good.
    # though, I am still figuring out what sorts of visualizations would be good in general.

    # prep the dict for json response simply return the list of dict items
    response = {}
    for key, value in df_dict.items():
        response[key] = value.to_dict(orient='records')

    try:
        problemType = data_dict["problemType"]
    except:
        if verbose:
            print("No problemType found in data_dict")
        raise ValueError("No problemType found in data_dict")
    
    if problemType == "solver":
        coverage_model(df_dict, data_dict)

    return jsonify(response)

def coverage_model(df_dict, data_dict):
    """
    Create a gurobi model from the dataframes and data_dict
    :param df_dict: dictionary of dataframes
    :param data_dict: dictionary of data
    :return: None
    """
    # convert the dataframes to dictionaries
    for key, value in df_dict.items():
        columns = value.columns.tolist()
        first_col = ""
        for i in range(len(columns)):
            cur_col = value.iloc[:, i].to_list()

            # try to convert the set strings to actual sets
            try:
                # TODO definite issue: mapping to int is not always correct
                cur_col = [set(map(int, c.strip('{}').split(','))) for c in cur_col]
            except:
                pass
        
            # make singular dicts first then combine them
            if i == 0:
                globals()[columns[i]] = value.iloc[:, i].to_list()
                first_col = cur_col
            else:
                new_dict = {first_col[i] : cur_col[i] for i in range(len(cur_col))}
                globals()[columns[i]] = new_dict
    
    # Comment: gurobi modelling examples usually use multidict, but as long as the first_col is unique, this should work
                
    # Create a new model
    m = gp.Model("coverage_model")
               
    # Finish parameters
    # TODO add parameters to the form
    """
    try:
        for key, value in data_dict["parameters"].items():
            globals()[key] = value
    except:
        if verbose:
            print("No parameters found in data_dict")
        raise ValueError("No parameters found in data_dict")
    """
    # Hard-coded for now
    budget = 20

    # Create variables
    try:
        variables = data_dict["variables"]
        for v in variables:
            var, Index = v.split("_")
            length = len(globals()[Index])
            globals()[var] = m.addVars(length, vtype=GRB.BINARY, name=v)
    except:
        if verbose:
            print("No variables found in data_dict")
        raise ValueError("No variables found in data_dict")

    # Add constraints
    try:
        for c in data_dict["constraints"]:
            c = parse(c)
            c = "m.addConstr(" + c + ")"
            exec(c)
    except:
        if verbose:
            print("No constraints found in data_dict")
        raise ValueError("No constraints found in data_dict")

    # Display Globals context
    if verbose:
        for key, value in globals().items():
            print(key, value)
        print("\n")

    # TODO: this constraint still needs more work to be generalized, hard-coding for now
    # to check if everything else is working
    m.addConstrs((gp.quicksum(build[t] for t in Tower if r in Coverage[t]) >= iscovered[r]
                        for r in Region), name="Build2cover")

    # Set objective
    try:
        obj = data_dict["objective"][0]
        obj = parse(obj)
        obj = "m.setObjective(" + obj + ", "
        obj += "GRB.MAXIMIZE" if data_dict["objective"][1].strip().lower() == "maximize" else "GRB.MINIMIZE"
        obj += ")"
        exec(obj)
    except:
        if verbose:
            print("No objective found in data_dict")
        raise ValueError("No objective found in data_dict")

    # Optimize
    m.optimize()

    # This solution print is also hard-coded to test functionality.
    # Shouldn't be too hard to generalize

    # Print the solution
    for tower in build.keys():
        if (abs(build[tower].x) > 1e-6):
            print(f"\n Build a cell tower at location Tower {tower}.")

    total_population = 0

    for region in range(len(Region)):
        total_population += Population[region]

    coverage = round(100*m.objVal/total_population, 2)

    print(f"\n The population coverage associated to the cell towers build plan is: {coverage} %")

    total_cost = 0

    for tower in range(len(Tower)):
        if (abs(build[tower].x) > 0.5):
            total_cost += Cost[tower]*int(build[tower].x)

    budget_consumption = round(100*total_cost/budget, 2)
    print(f"\n The percentage of budget consumed associated to the cell towers build plan is: {budget_consumption} %")


if __name__ == '__main__':
    app.run(debug=True, port=8080)
