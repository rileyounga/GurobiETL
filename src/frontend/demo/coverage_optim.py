import pandas as pd
import gurobipy as gp
from utils import parse, typeparse
from gurobipy import GRB

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

    # Create the variables
    variables = []
    for v in data_dict["variables"]:
        var, Index = v.split("^")
        h1, h2 = Index.replace("{", "").replace("}", "").split(",") if "," in Index else (Index.replace("{", "").replace("}", ""), None)
        if h2 == None:
            globals()[var] = m.addVars(globals()[h1], vtype=GRB.BINARY)
        else:
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

    return result

def main():
    files = ["coverage.csv", "population.csv"]
    data_dict = {
        "variables": ["build^{Tower}", "iscovered^{Region}"],
        "objective": {"formula": "/sum_r^{Region} (iscovered_r * Population_r)", "sense": "maximize"},
        "constraints": ["/sum_t^{Tower} (build_t * Cost_t) <= 20",
                        "/sum_t^{Tower} (build_t if r in Coverage_t) >= iscovered_{r} /forall_r^{Region}"],

    }
    result = general_model(data_dict, files, "Coverage")
    print(result)

if __name__ == "__main__":
    main()