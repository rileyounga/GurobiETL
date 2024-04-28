import pandas as pd
import gurobipy as gp
from utils import parse, typeparse
from gurobipy import GRB
import matplotlib.pyplot as plt
import seaborn as sns

verbose = False
        
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
                # since the first row is index, int/float dtype is assumed
                globals()[key] = value.to_list()
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
    for v in data_dict["variables"]:
        var, Index = v.split("^")
        h1, h2 = Index.replace("{", "").replace("}", "").split(",") if "," in Index else (Index.replace("{", "").replace("}", ""), None)
        if h2 == None:
            globals()[var] = m.addVars(globals()[h1], vtype=GRB.BINARY)
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
            globals()[var] = m.addVars(globals()[h1], globals()[h2], vtype=GRB.BINARY)
        variables.append(var)

    # Add the constraints and objective
    for c in data_dict["constraints"]:
        cons = parse(c)
        # count the number of 'for's in the constraint
        iter_count = cons.count("for")
        if iter_count == 1:
            if verbose:
                print("m.addConstr(" + cons + ")")
            exec("m.addConstr(" + cons + ")")
        elif iter_count == 2:
            if verbose:
                print("m.addConstrs(" + cons + ")")
            exec("m.addConstrs(" + cons + ")")

    objective = data_dict["objective"]["formula"]
    sense = "GRB.MAXIMIZE" if data_dict["objective"]["sense"].strip().lower() == "maximize" else "GRB.MINIMIZE"
    obj = "m.setObjective(" + parse(objective) + ", sense=" + sense + ")"
    if verbose:
        print(obj)
    exec(obj)

    m.optimize()

    if m.status == GRB.INFEASIBLE:
        return "Model is infeasible"
    
    # Print the decision variables
    result = "\nDecision Variables:\n"

    for v in variables:
        result += f"{v}: \n"
        for key, value in globals()[v].items():
            result += f"{key}: {value.x}\n"

    if hardcode == "PowerPlant":
        supply = plot_power_plant_supply(globals()["H"], globals()["P"], globals()["z"])
        demand = plot_power_demand(globals()["H"], globals()["d"])

    return result

def plot_power_plant_supply(H, P, Z):
    """
    Plot power plant supply
    :param H: list of hours
    :param P: list of plants
    :param Z: gurobi variable
    :return: None
    """

    solution = pd.DataFrame() 
    solution = pd.DataFrame(columns=['Hour', 'Power (MWh)', 'Plant']) 
    plant_hour_pairs = [(h,i) for i in P for h in H if Z[i,h].X > 0] 
                
    solution['Hour'] = [pair[0] for pair in plant_hour_pairs]
    solution['Plant'] = [pair[1] for pair in plant_hour_pairs]
    solution['Power generated (MWh)'] = [Z[pair[1],pair[0]].X for pair in plant_hour_pairs]
                
    print("Power supply:")
    fig, ax = plt.subplots(figsize=(15,6)) 
    sns.pointplot(data=solution,x='Hour', y='Power generated (MWh)', hue='Plant')
    sns.move_legend(ax, "upper left", bbox_to_anchor=(1, 1))
    plt.show()

    return fig

def plot_power_demand(H, D):
    """
    Plot power demand
    :param H: list of hours
    :param D: dictionary of demand
    :return: None
    """

    print("Power demand:")
    fig, ax = plt.subplots(figsize=(15,6)) 
    demand = pd.DataFrame(columns=['Hour', 'Demand (MWh)']) 
    demand['Hour'] = list(H)
    demand['Demand (MWh)'] = [D[h] for h in H]
    sns.pointplot(data=demand,x='Hour', y='Demand (MWh)')
    plt.show()
    
    return fig

def main():
    files = ["fixed_costs_revised.csv", "demand.csv", "fuel_costs.csv", "startup_costs.csv", "plant_capacities.csv", "operating_costs.csv"]
    data_dict = {
        "objective": {"formula": "/sum_i^{Plant} /sum_h^{H} (f_i * z_{i,h} + o_i * u_{i,h} + s_i * v_{i,h} + t_i * w_{i,h})", "sense": "minimize"},
        "constraints": ["/sum_i^{Plant} z_{i,h} = d_h /forall_h^{H}",
                        
                        "z_{i,h} <= Capacity_i * u_{i,h} /forall_i^{Plant} /forall_h^{H}",
                        "z_{i,h} >= m_i * Capacity_i * u_{i,h} /forall_i^{Plant} /forall_h^{H}",

                        "z_{i,h} >= m_i * Capacity_i /forall_i^{P_N} /forall_h^{H}",

                        "z_{i,h} - z_{i,h-1} >= -r_i * Capacity_i /forall_i^{Plant} /forall_h^{H} if h > 1",
                        "z_{i,h} - z_{i,h-1} <= r_i * Capacity_i /forall_i^{Plant} /forall_h^{H} if h > 1",

                        "v_{i,h} <= u_{i,h} /forall_i^{Plant} /forall_h^{H}",
                        "w_{i,h} <= 1 - u_{i,h} /forall_i^{Plant} /forall_h^{H}",
                        
                        "v_{i,h} - w_{i,h} = u_{i,h} - u_{i,h-1} /forall_i^{Plant} /forall_h^{H} if h > 1",
                        ],
        "variables": ["z^{Plant,H}", "u^{Plant,H}", "v^{Plant,H}", "w^{Plant,H}"]
    }
    result = general_model(data_dict, files, hardcode="PowerPlant")
    print(result)

if __name__ == "__main__":
    main()