import pandas as pd
import gurobipy as gp
from utils import parse, typeparse
from gurobipy import GRB
import ast
import matplotlib.pyplot as plt
import networkx as nx

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
        if hardcode == "Powerplant":
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

    tree = plot_coverage_tree()
    return result

def plot_coverage_tree():
    """
    Create a tree matching selected Towers to their Coverage Regions.
    Highlight the selected Towers, but display all Towers and Regions.
    """

    for key, value in globals().items():
        print(key, value, type(value))

    # Find the coverage by extracting the first global variable mapping indexes to sets
    for var in globals():
        if isinstance(globals()[var], dict) and len(globals()[var]) > 0 and isinstance(list(globals()[var].values())[0], set):
            coverage = globals()[var]
            break

    # Find the regions by extracting the longest global variable list
    max_len = 0
    for var in globals():
        if isinstance(globals()[var], list) and len(globals()[var]) > max_len:
            region = globals()[var]
            max_len = len(globals()[var])


    # Find the selected Towers by extracting the global variable with the same indexes as the coverage that is also a gurobi variable
    for var in globals():
        if isinstance(globals()[var], gp.tupledict) and len(globals()[var]) > 0 and set(globals()[var].keys()) == set(coverage.keys()):
            selected = globals()[var]
            break

    # Find the covered regions by extracting the global variable with the same indexes as the regions that is also a gurobi variable
    for var in globals():
        if isinstance(globals()[var], gp.tupledict) and len(globals()[var]) > 0 and set(globals()[var].keys()) == set(region):
            covered = globals()[var]
            break

    print(coverage)
    print(region)
    print(selected)
    print(covered)

    # now coverage is a dictionary mapping ints to sets
    # region is a list of ints
    # selected is a gurobi variable mapping ints to gb.Var (binary)

    G = nx.DiGraph()

    # Add the nodes
    for r in region:
        # if the region is covered, color it lightblue
        if covered[r].x == 1:
            G.add_node(f"Region_{r}", pos=(0, list(region).index(r)), color='lightblue')
        else:
            # if the region is not covered, color it red
            G.add_node(f"Region_{r}", pos=(0, list(region).index(r)), color='red')

    for t in coverage:
        # If the tower is selected, color it blue
        if selected[t].x == 1:
            G.add_node(f"Tower_{t}", pos=(1, list(coverage.keys()).index(t)), color='blue')
        else:
            # If the tower is not selected, color it grey
            G.add_node(f"Tower_{t}", pos=(1, list(coverage.keys()).index(t)), color='grey')

    # Add the edges
    for t in selected:
        for r in coverage[t]:
            # If the tower is selected, color the edge blue
            if selected[t].x == 1:
                G.add_edge(f"Tower_{t}", f"Region_{r}", color='blue', weight=2)
            else:
                # If the tower is not selected, color the edge grey
                G.add_edge(f"Tower_{t}", f"Region_{r}", color='grey', weight=0.1)

    # Draw the graph
    pos = nx.get_node_attributes(G, 'pos')
    nodes_color = [G.nodes[n].get('color', 'grey') for n in G.nodes()]  # Use a default color if no color attribute is found
    edges_color = nx.get_edge_attributes(G, 'color')
    edges_weight = nx.get_edge_attributes(G, 'weight')  # Get the edge weights
    # find the max length of a node name to set the node size
    max_length = max([len(n) for n in G.nodes()])
    nx.draw(G, pos, with_labels=True, node_color=nodes_color, edge_color=list(edges_color.values()), 
            edgecolors='grey', node_size=max_length*100, font_size=8, font_color='black', font_weight='bold')
    nx.draw_networkx_edges(G, pos, edge_color=list(edges_color.values()), width=list(edges_weight.values()))  # Draw the edges with weights
    plt.show()


def main():
    files = ["coverage.csv", "population.csv"]
    data_dict = {
        "variables": ["build^{Tower}", "iscovered^{Region}"],
        "objective": {"formula": "/sum_r^{Region} (iscovered_r * Population_r)", "sense": "maximize"},
        "constraints": ["/sum_t^{Tower} (build_t * Cost_t) <= 20",
                        "/sum_t^{Tower} (build_t if r in Coverage_t) >= iscovered_{r} /forall_r^{Region}"],

    }

    result = general_model(data_dict, files, "Coverage")
    #print(result)

if __name__ == "__main__":
    main()