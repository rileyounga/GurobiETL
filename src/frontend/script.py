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

from utils import parse, typeparse

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
    if verbose:
        print("Got input:", data_dict)

    # request.files is an ImmutableMultiDict of files found in the request.
    # Each file is tied to a key named 'file'.
    # If we upload three files, there will be three distinct keys named 'file'.
    # The getlist('file') method constructs a list of all files, each
    # represented using the FileStorage class:
    # https://tedboy.github.io/flask/generated/generated/werkzeug.FileStorage.html
    files = request.files.getlist('file')
    if verbose:
        print("Got files:", [file.filename for file in files])

    # prep the dict for json response simply return the list of dict items
    response = {}

    try:
        problemType = data_dict["problem"]
    except:
        return jsonify({"error": "Please select a problem type"})
    
    if problemType == "mathematical_optimization":
        result = general_model(data_dict, files, hardcode="PowerPlant")
        response["result"] = result
        if verbose:
            print(result)

    elif problemType == "location_analysis":
        result = general_model(data_dict, files)
        response["result"] = result
        if verbose:
            print(result)

    elif problemType == "portfolio_optimization":
        result, fig = portfolio_model(files)
        response["result"] = result
        if verbose:
            print(result)
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

def portfolio_model(files):
    """
    Create a gurobi model from the dataframes and data_dict
    :param files: dictionary of dataframes
    :param data_dict: dictionary of data
    :return: None
    """
    # Load the data
    try:
        stocks = pd.read_csv(files[0])
    except:
        return "Error: Please upload a csv file with a list of stocks"
    stocks = stocks.iloc[1:, 0].str.upper().str.strip().tolist()
    try:
        data = yf.download(stocks, period="2y")
    except:
        return "Error: Please check the stock symbols and try again"
    
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
    for f in files:
        try:
            file = pd.read_csv(f)
        except:
            return "Error: Please upload a csv file"
        if hardcode == "PowerPlant":
            globals()[f.split(".")[0]] = pd.read_csv(f)
        # Parameterize the files
        i = 0
        for key, value in file.items():
            key = key.strip()
            # The first column is the index for the rest of the column dictionaries
            if i == 0:
                # since the first row is index, int/float dtype is assumed
                try:
                    globals()[key] = value.to_list()
                except:
                    return "Error: First column must be index"
                index = value.to_list()
            else:
                # parse the data type of the value
                column = [typeparse(value[i]) for i in range(len(value))]
                globals()[key] = {index[i]: column[i] for i in range(len(column))}
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
        i = 0

    # Create the variables
    variables = []
    try:
        var_test = data_dict["variables"]
    except:
        return "Error: Please add variables to the data"
    for v in data_dict["variables"]:
        var, Index = v.split("^")
        h1, h2 = Index.replace("{", "").replace("}", "").split(",") if "," in Index else (Index.replace("{", "").replace("}", ""), None)
        if h2 == None:
            try:
                globals()[var] = m.addVars(globals()[h1], vtype=GRB.BINARY)
            except:
                return "Error: Please check the variable names"
        else:
            if hardcode == "PowerPlant":
                # This could be fixed if there was more time, an oversight on my part, I thought I could intuit the vtype
                # from the data, but it seems like it needs to be a parameter in the data_dict
                # So I will hardcode the vtype here for the first powerplant variable
                if i == 0:
                    globals()[var] = m.addVars(globals()[h1], globals()[h2], lb=0)
                    print("m.addVars(" + h1 + ", " + h2 + ", lb=0)")
                    i += 1
                    variables.append(var)
                    continue
            try:
                globals()[var] = m.addVars(globals()[h1], globals()[h2], vtype=GRB.BINARY)
            except:
                return "Error: Please check the variable names"
        variables.append(var)

    # Add the constraints and objective
    try:
        cons_test = data_dict["constraints"]
    except:
        return "Error: Please add constraints to the data"
    for c in data_dict["constraints"]:
        cons = parse(c)
        # count the number of 'for's in the constraint
        iter_count = cons.count("for")
        if iter_count == 1:
            if verbose:
                print("m.addConstr(" + cons + ")")
            try:
                exec("m.addConstr(" + cons + ")")
            except:
                return "Error: Please check the constraint"
        elif iter_count == 2:
            if verbose:
                print("m.addConstrs(" + cons + ")")
            try:
                exec("m.addConstrs(" + cons + ")")
            except:
                return "Error: Please check the constraint"
    try:
        obj_test = data_dict["objective"]
    except:
        return "Error: Please add an objective to the data"
    objective = data_dict["objective"]["formula"]
    sense = "GRB.MAXIMIZE" if data_dict["objective"]["sense"].strip().lower() == "maximize" else "GRB.MINIMIZE"
    obj = "m.setObjective(" + parse(objective) + ", sense=" + sense + ")"
    if verbose:
        print(obj)
    try:
        exec(obj)
    except:
        return "Error: Please check the objective"

    m.optimize()

    if m.status == GRB.INFEASIBLE:
        return "Model is infeasible"
    
    # Print the decision variables
    result = "\nDecision Variables:\n"

    for v in variables:
        result += f"{v}: \n"
        for key, value in globals()[v].items():
            result += f"{key}: {value.x}\n"

    if hardcode == "PowerPlant" and verbose:
        import matplotlib.pyplot as plt
        import seaborn as sns

        solution = pd.DataFrame() 
        solution = pd.DataFrame(columns=['Hour', 'Power (MWh)', 'Plant']) 
        plant_hour_pairs = [(h,i) for i in globals()["P"] for h in globals()["H"]  if globals()["z"][i,h].X > 0] 
                    
        solution['Hour'] = [pair[0] for pair in plant_hour_pairs]
        solution['Plant'] = [pair[1] for pair in plant_hour_pairs]
        solution['Power generated (MWh)'] = [globals()["z"][pair[1],pair[0]].X for pair in plant_hour_pairs]
                    
        print("Power supply:")
        fig, ax = plt.subplots(figsize=(15,6)) 
        sns.pointplot(data=solution,x='Hour', y='Power generated (MWh)', hue='Plant')
        sns.move_legend(ax, "upper left", bbox_to_anchor=(1, 1))
        plt.show()

        print("Power demand:")
        fig, ax = plt.subplots(figsize=(15,6)) 
        demand = pd.DataFrame(columns=['Hour', 'Demand (MWh)']) 
        demand['Hour'] = list(globals()["H"])
        demand['Demand (MWh)'] = [globals()["d"][h] for h in globals()["H"]]
        sns.pointplot(data=demand,x='Hour', y='Demand (MWh)')
        plt.show() 

    return result

if __name__ == '__main__':
    app.run(debug=True, port=8080)
