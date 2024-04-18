import math
import io
import json
import base64
import yfinance as yf
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import gurobipy as gp
from gurobipy import GRB
from flask import Flask, request, jsonify
from flask_cors import CORS
from matplotlib.backends.backend_agg import FigureCanvasAgg as FigureCanvas

from utils import parse, parse_data

"""
Context:
#fetch path: src/app/problem/page.js
#cur path: src/api/script.py
"""

app = Flask(__name__)
CORS(app)
CORS(app, resources={r"/api/*": {"origins": "http://localhost:3000"}})
verbose=True

@app.route('/api/home', methods=['POST'])
def home():
    # 'data' is an 'ImmutableMultiDict'. See the following documentation:
    # https://tedboy.github.io/flask/generated/generated/werkzeug.ImmutableMultiDict.html
    data = request.form
    data_dict = {key: json.loads(value) for (key, value) in zip(data.keys(), data.values())}
    print("Got input:", data_dict)
    #TODO: This is the new form data I need:
    # I cut parameters, they can be set with the variables, and I didn't realize till now, but I still need an input form
    # to go with the objective
    # Also the portfolio opimization model just needs the files, so you can get rid of the form data for that one
    """{
        "objective": ["/sum_i^{Plant} /sum_h^{H} (f_i * z_{i,h} + o_i * u_{i,h} + s_i * v_{i,h} + t_i * w_{i,h})", "minimize"],
        "constraints": ["/sum_i^{Plant} z_{i,h} = d_h /forall_h^{H}",
                        "z_{i,h} <= Capacity_i * u_{i,h} /forall_i^{Plant} /forall_h^{H}",
                        #"z_{i,h} >= m_i * c_i * u_{i,h}",
                        #"v_{i,h} <= u_{i,h}",
                        #"w_{i,h} <= 1 - u_{i,h}"
                        ],
        "variables": ["z^{Plant,H}", "u^{Plant,H}", "v^{Plant,H}", "w^{Plant,H}"]
    }"""

    # request.files is an ImmutableMultiDict of files found in the request.
    # Each file is tied to a key named 'file'.
    # If we upload three files, there will be three distinct keys named 'file'.
    # The getlist('file') method constructs a list of all files, each
    # represented using the FileStorage class:
    # https://tedboy.github.io/flask/generated/generated/werkzeug.FileStorage.html
    files = request.files.getlist('file')
    print("Got files:", [file.filename for file in files])

    # prep the dict for json response simply return the list of dict items
    response = {}

    problemType = data_dict["problem"]
    
    if problemType == "mathematical_optimization":
        result = general_model(data_dict, files, hardcode="PowerPlant")
        response["result"] = result

    elif problemType == "coverage_model":
        result = coverage_model(data_dict, files, hardcode="Coverage")
        response["result"] = result

    elif problemType == "portfolio_optimization":
        result, fig = portfolio_model(files)
        response["result"] = result
        response["fig"] = base64.b64encode(fig).decode()
        """
        To be used by the frontend like so:
        fetch('/get_image')
            .then(response => response.json())
            .then(data => {
                let img = document.createElement('img');
                img.src = data.image;
                document.body.appendChild(img);
            });
        """

    return jsonify(response)

def coverage_model(df_dict, data_dict):
    #TODO: I working to convert this function to the new implementation
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
                
    # Create a new model
    m = gp.Model("coverage_model")        
    
    try:
        for key, value in data_dict["parameters"].items():
            globals()[key] = value
    except:
        if verbose:
            print("No parameters found in data_dict")
        raise ValueError("No parameters found in data_dict")

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

def portfolio_model(files):
    """
    Create a gurobi model from the dataframes and data_dict
    :param files: dictionary of dataframes
    :param data_dict: dictionary of data
    :return: None
    """
    # Load the data
    stocks = pd.read_csv(files[0])
    stocks = stocks.iloc[1:, 0].str.upper().str.strip().tolist()
    data = yf.download(stocks, period="2y")
    
    # Compute statistics
    closes = np.transpose(data['Close'].to_numpy())
    absdiffs = np.abs(np.diff(closes))
    reldiffs = absdiffs / closes[:, :-1]
    delta = np.mean(reldiffs, axis=1)
    sigma = np.cov(reldiffs)
    std = np.std(reldiffs, axis=1)

    m = gp.Model("portfolio")
    x = m.addMVar(len(stocks))

    # Objective is to minimize risk while maximizing return
    portfolio_risk = x @ sigma @ x
    m.setObjective(portfolio_risk, GRB.MINIMIZE)

    # Fix budget with a constraint
    m.addConstr(x.sum() == 1, "Budget")

    m.optimize()

    #TODO: decide how we want to display the results
    # for now, I'll just build a string to jsonify return

    # Print the optimal portfolio
    result = "\nOptimal Portfolio:\n"
    for i in range(len(stocks)):
        # if stock allocation is less than 0.01, then it is considered negligible
        if x.X[i] > 0.01:
            # print the stock and its allocation as a percentage
            result += f"{stocks[i]}: {x.X[i]*100:.2f}%\n"

    fig = plot_portfolio(m, x, delta, std, stocks)
    return result, fig

def plot_portfolio(m, x, delta, std, stocks):
    """
    Plot the efficient frontier
    :param m: gurobi model
    :param x: gurobi variable
    :param delta: numpy array
    :param std: numpy array
    :param stocks: list
    :return: None
    """
    # Plot the efficient frontier
    minrisk_volatility = math.sqrt(m.ObjVal)
    minrisk_return = delta @ x.X
    # Create an expression representing the expected return for the portfolio
    portfolio_return = delta @ x
    target = m.addConstr(portfolio_return == minrisk_return, 'target')

    # Solve for efficient frontier by varying target return
    frontier = np.empty((2,0))
    for r in np.linspace(delta.min(), delta.max(), 15):
        target.rhs = r
        m.optimize()
        frontier = np.append(frontier, [[math.sqrt(m.ObjVal)],[r]], axis=1)

    fig, ax = plt.subplots(figsize=(10,8))

    # Plot volatility versus expected return for individual stocks
    ax.scatter(x=std, y=delta,
            color='Blue', label='Individual Stocks')
    for i, stock in enumerate(stocks):
        ax.annotate(stock, (std[i], delta[i]))

    # Plot volatility versus expected return for minimum risk portfolio
    ax.scatter(x=minrisk_volatility, y=minrisk_return, color='DarkGreen')
    ax.annotate('Minimum\nRisk\nPortfolio', (minrisk_volatility, minrisk_return),
                horizontalalignment='right')

    # Plot efficient frontier
    ax.plot(frontier[0], frontier[1], label='Efficient Frontier', color='DarkGreen')

    # Format and display the final plot
    ax.set_xlabel('Volatility (standard deviation)')
    ax.set_ylabel('Expected Return')
    ax.legend()
    ax.grid()
    
    output = io.BytesIO()
    FigureCanvas(fig).print_png(output)
    return output.getvalue()

def general_model(data_dict, files, hardcode="None"):
    """
    Create a gurobi model from the dataframes and data_dict
    :param data_dict: dictionary of data
    :param files: list of file names
    :param hardcode: string to determine which model to run
    :return: None
    """
    m = gp.Model("general_model")
    
    # Load the data
    j = 0
    for f in files:
        name = f.filename.split(".")[0]
        data = io.BytesIO(f.read())
        j += 1
        file = pd.read_csv(data)
        if hardcode == "PowerPlant":
            globals()[name] = file
        # Parameteric the files
        i = 0
        for key, value in file.items():
            key = key.strip()
            # The first column is the index for the rest of the column dictionaries
            if i == 0:
                globals()[key] = {value[i] for i in range(len(value))}
                index = value.to_list()
            else:
                globals()[key] = {index[i]: value[i] for i in range(len(value))}
            i += 1

    # Power Plant Hardcoded Data
    if hardcode == "PowerPlant":
        date = "2011-07-01"
        year = int(date.split("-")[0])
        month = int(date.split("-")[1])
        day = int(date.split("-")[2])
        # unfortunately the example problem performs data operations after loading the data, 
        # something that can't be handled by the current implementation so we have to hardcode
        # the data here, If I have time I will look into this bit more
        globals()["d"] = globals()["demand"][(globals()["demand"]["YEAR"]==year)&(globals()["demand"]["MONTH"]==month)&(globals()["demand"]["DAY"]==day)].set_index(["HOUR"]).LOAD.to_dict()
        globals()["H"] = set(globals()["d"].keys())
        globals()["P"] = set(globals()["plant_capacities"]["Plant"].unique())
        globals()["p_type"] = globals()["plant_capacities"].set_index(["Plant"]).PlantType.to_dict()
        globals()["P_N"] = set([i for i in globals()["P"] if globals()["p_type"][i]=="NUCLEAR"])
        globals()["fuel_type"] = globals()["plant_capacities"].set_index(["Plant"]).FuelType.to_dict()
        globals()["c"] = globals()["plant_capacities"].set_index(["Plant"]).Capacity.to_dict()
        globals()["f"] = {i: globals()["fuel_costs"].T.to_dict()[9][globals()["fuel_type"][i]] for i in globals()["fuel_type"].keys()}
        globals()["o"] = {i: globals()["operating_costs"][globals()["operating_costs"]['year']==year].T.to_dict()[9][globals()["fuel_type"][i]] for i in globals()["fuel_type"].keys()}
        globals()["s"] = {i: globals()["startup_costs"][globals()["startup_costs"]['year']==year].T.to_dict()[9][globals()["fuel_type"][i]] for i in globals()["fuel_type"].keys()}
        globals()["t"] = globals()["s"].copy()
        globals()["m"] = {i: 0.8 if i in globals()["P_N"] else 0.01 for i in globals()["P"]}
        globals()["r"] = {i: 1 if i in ["BIOMASS", "GAS", "HYDRO", "OIL"] else .2 if i in globals()["P_N"] else .25 for i in globals()["P"]}

    elif hardcode == "Coverage":
        pass

    # Create the variables
    variables = []
    for v in data_dict["variables"]:
        var, Index = v.split("^")
        h1, h2 = Index.replace("{", "").replace("}", "").split(",") if "," in Index else (Index.replace("{", "").replace("}", ""), None)
        if h2 == None:
            globals()[var] = m.addVars(globals()[h1])
        else:
            globals()[var] = m.addVars(globals()[h1], globals()[h2])
        variables.append(var)

    # Add the constraints and objective
    for c in data_dict["constraints"]:
        cons = parse(c)
        exec("m.addConstrs(" + cons + ")")

    objective = data_dict["objective"][0]
    sense = "GRB.MAXIMIZE" if data_dict["objective"][1].strip().lower() == "maximize" else "GRB.MINIMIZE"
    obj = "m.setObjective(" + parse(objective) + ", sense=" + sense + ")"
    print(obj)
    exec(obj)

    m.optimize()                

    # Print the decision variables
    result = "\nDecision Variables:\n"

    for v in variables:
        result += f"{v}: \n"
        for key, value in globals()[v].items():
            result += f"{key}: {value.x}\n"

    return result

if __name__ == '__main__':
    app.run(debug=True, port=8080)
