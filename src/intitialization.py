import numpy as np
import pandas as pd
import gurobipy as gp
from gurobipy import GRB
import argparse

"""
Read a command line arguement from react app and initialize the model.
    The react app will send a file (csv, xls, more later) to the server. 
    Additionally, the react app will send a json file with the following format:
    {
        "data": "path/to/file",
        "problem": "linear programming",
        "variables": {
            "x1": "continuous", (this might be able to be generated based on the float format of the input)
            "x2": "continuous"
        },
        "objective": "maximize",
        (ignore constraints for now, they are by far the most complex part of this problem.)
        "constraints": {
            "c1": "x1 + x2 <= 10",
            "c2": "x1 - x2 <= 20",
            "c3": "x1 + 3x2 <= 25"
        }
    }
"""

# Read the command line arguement
parser = argparse.ArgumentParser()
parser.add_argument("data", help="path to the data file")
parser.add_argument("problem", help="type of problem")
parser.add_argument("variables", help="variables and their types")
parser.add_argument("objective", help="objective function")
parser.add_argument("constraints", help="constraints")
args = parser.parse_args()

# Read the data file
data = args.data
df = pd.read_csv(data)

# Initialize the model
model = gp.Model("model")

# Create the variables
variables = args.variables

# Create the objective function
objective = args.objective

# Create the constraints
constraints = args.constraints

# Add the variables to the model
for variable in variables:
    if variables[variable] == "continuous":
        model.addVar(lb=0, ub=GRB.INFINITY, vtype=GRB.CONTINUOUS, name=variable)
    elif variables[variable] == "integer":
        model.addVar(lb=0, ub=GRB.INFINITY, vtype=GRB.INTEGER, name=variable)
    elif variables[variable] == "binary":
        model.addVar(lb=0, ub=1, vtype=GRB.BINARY, name=variable)
    else:
        print("Invalid variable type")


# Add the objective function to the model
if objective == "maximize":
    model.setObjective(gp.quicksum(variables[variable] for variable in variables), GRB.MAXIMIZE)
elif objective == "minimize":
    model.setObjective(gp.quicksum(variables[variable] for variable in variables), GRB.MINIMIZE)

# Add the constraints to the model
for constraint in constraints:
    model.addConstr(gp.quicksum(variables[variable] for variable in variables) <= constraints[constraint])

# Optimize the model
model.optimize()

# Return the results
results = {}
for variable in variables:
    results[variable] = variables[variable].x

print(results)

# Once I have the results, rather than sending it to a seperate py file, it might be better to have it all in one
# so its easier to send back to the react app.