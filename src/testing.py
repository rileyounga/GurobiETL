import re
import yfinance as yf
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import gurobipy as gp
from gurobipy import GRB

def parse(expr):
    """
    Parse the expression to be used in the gurobi model
    :param expr: string
    :param sets: dictionary
    :return: string
    """
    ret = ""
    # split on ==, <=, >=, <, >, != if it exists
    operator = re.findall(r"=|<=|>=|<|>|!=", expr)
    
    # if there is an operator, we need to split the expression
    if len(operator) > 0:
        ret += "("
        # find the sums
        sums = re.findall(r"/sum_(\w)\^{(\w+)}", expr)
        if len(sums) > 0:
            ret += "gp.quicksum("
        # now that we extracted the info from the sums, we can remove them
        expr = re.sub(r"/sum_(\w)\^{(\w+)}", "", expr)

        #split
        expr = expr.split(operator[0])
        lhs = expr[0].strip()
        rhs = expr[1].strip()

        # also remove parentheses
        lhs = lhs.replace("(", "").replace(")", "")
        rhs = rhs.replace("(", "").replace(")", "")
        # remove whitespace
        lhs = lhs.strip()
        rhs = rhs.strip()

        # find the subscripts to replace with array notation
        subscripts = re.findall(r"(\w_\w+|\w_\{\w+,\w+\})", lhs)
        for subscript in subscripts:
            if "{" not in subscript:
                lhs = lhs.replace(subscript, f"{subscript.split('_')[0]}[{subscript.split('_')[1]}]")
            else:
                lhs = lhs.replace(subscript, f"{subscript.split('_')[0]}[{subscript.split('_')[1].replace('{', '').replace('}', '')}]")

        ret += lhs

        # Add the sums for the lhs
        for sum in sums:
            ret += f" for {sum[0]} in {sum[1]}"
        if len(sums) > 0:
            ret += ")"

        if operator[0] == "=":
            operator[0] = "=="
        ret += f" {operator[0]} "

        # Check if there is a forall statement
        forall = re.findall(r"/forall_(\w)\^{(\w+)}", rhs)
        rhs = re.sub(r"/forall_(\w)\^{(\w+)}", "", rhs)

        subscripts = re.findall(r"(\w_\w+|\w_\{\w+,\w+\})", rhs)
        for subscript in subscripts:
            if "{" not in subscript:
                rhs = rhs.replace(subscript, f"{subscript.split('_')[0]}[{subscript.split('_')[1]}]")
            else:
                rhs = rhs.replace(subscript, f"{subscript.split('_')[0]}[{subscript.split('_')[1].replace('{', '').replace('}', '')}]")

        ret += rhs

        ret += ")"
        
        for f in forall:
            ret += f" for {f[0]} in {f[1]}"

    else:
        indexes = re.findall(r"(\w_\w+|\w_\{\w+,\w+\})", expr)
        index = set()
        for idx in indexes:
            if "{" not in idx:
                index.add(idx.split("_")[1])
            else:
                for i in idx.split("_")[1].replace("{", "").replace("}", "").split(","):
                    index.add(i)

        sums = re.findall(r"/sum_(\w)\^{(\w+)}", expr)  # Modified regex pattern
        if len(sums) > 0:
            ret += "gp.quicksum("
        for sum in sums:
            for idx in index.copy():
                if sum[0] == idx:
                    index.remove(idx)

        expr = re.sub(r"/sum_(\w)\^{(\w+)}", "", expr)  # Modified regex pattern
        expr = expr.replace("(", "").replace(")", "")
        expr = expr.strip()

        subscripts = re.findall(r"(\w_\w+|\w_\{\w+,\w+\})", expr)
        for subscript in subscripts:
            if "{" not in subscript:
                expr = expr.replace(subscript, f"{subscript.split('_')[0]}[{subscript.split('_')[1]}]")
            else:
                expr = expr.replace(subscript, f"{subscript.split('_')[0]}[{subscript.split('_')[1].replace('{', '').replace('}', '')}]")

        ret += expr

        for sum in sums:
            ret += f" for {sum[0]} in {sum[1]}"


        if len(sums) > 0:
            ret += ")"
        elif len(index) > 0:
            ret += ")"

    return ret

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
        file = pd.read_csv(f)
        if hardcode == "PowerPlant":
            globals()[f.split(".")[0]] = pd.read_csv(f)
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

def main():
    powerplant = False
    coverage = True
    if powerplant:
        files = ["fixed_costs_revised.csv", "demand.csv", "fuel_costs.csv", "startup_costs.csv", "plant_capacities.csv", "operating_costs.csv"]
        data_dict = {
            "objective": ["/sum_i^{Plant} /sum_h^{H} (f_i * z_{i,h} + o_i * u_{i,h} + s_i * v_{i,h} + t_i * w_{i,h})", "minimize"],
            "constraints": ["/sum_i^{Plant} z_{i,h} = d_h /forall_h^{H}",
                            "z_{i,h} <= Capacity_i * u_{i,h} /forall_i^{Plant} /forall_h^{H}",
                            #"z_{i,h} >= m_i * c_i * u_{i,h}",
                            #"v_{i,h} <= u_{i,h}",
                            #"w_{i,h} <= 1 - u_{i,h}"
                            ],
            "variables": ["z^{Plant,H}", "u^{Plant,H}", "v^{Plant,H}", "w^{Plant,H}"]
        }
    elif coverage:
        files = ["coverage.csv", "population.csv"]
        data_dict = {
            "objective": ["/sum_r^{Region} /sum_t^{Tower} (build_t)", "maximize"],
            "constraints": ["/sum_t^{Tower} (build_t) >= iscovered_r /forall_r^{Region}"],
            "variables": ["build^{Tower}", "iscovered^{Region}"]
        }
    result = general_model(data_dict, files, hardcode="PowerPlant")
    print(result)

if __name__ == "__main__":
    main()