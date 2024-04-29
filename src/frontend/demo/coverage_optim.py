import numpy as np
import pandas as pd
import gurobipy as gp
from utils import parse, typeparse
from gurobipy import GRB
import matplotlib.pyplot as plt
import networkx as nx
from scipy.spatial import Voronoi, voronoi_plot_2d
import matplotlib.animation as animation

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

    

    coverage, region, selected, covered = extract_data_for_visualization()

    create_voronoi_diagram(coverage, region, selected, covered)
    plot_comparative_analysis(coverage, region, selected, covered)
    frames = plot_growth()
    # Create the animation
    fig = plt.figure(figsize=(10, 8))
    ani = animation.FuncAnimation(fig, update, frames=frames, blit=False, repeat=False)
    plt.show()


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

def plot_growth():
    """
    Generate frames for the animated growth visualization.
    """
    # Find coverage, regions, selected towers, and covered regions
    for var in globals():
        if isinstance(globals()[var], dict) and len(globals()[var]) > 0 and isinstance(list(globals()[var].values())[0], set):
            coverage = globals()[var]
            break

    max_len = 0
    for var in globals():
        if isinstance(globals()[var], list) and len(globals()[var]) > max_len:
            region = globals()[var]
            max_len = len(globals()[var])

    for var in globals():
        if isinstance(globals()[var], gp.tupledict) and len(globals()[var]) > 0 and set(globals()[var].keys()) == set(coverage.keys()):
            selected = globals()[var]
            break

    for var in globals():
        if isinstance(globals()[var], gp.tupledict) and len(globals()[var]) > 0 and set(globals()[var].keys()) == set(region):
            covered = globals()[var]
            break

    # Generate frames for animation
    frames = []
    for t in coverage:
        G = nx.DiGraph()

        # Add the nodes
        for r in region:
            if covered[r].x == 1:
                G.add_node(f"Region_{r}", pos=(0, list(region).index(r)), color='lightblue')
            else:
                G.add_node(f"Region_{r}", pos=(0, list(region).index(r)), color='red')

        for t_idx in selected:  # Iterate over selected tower indices
            if t_idx <= t and selected[t_idx].x == 1:  # Add tower only if it is selected
                G.add_node(f"Tower_{t_idx}", pos=(1, list(coverage.keys()).index(t_idx)), color='blue')
            else:
                G.add_node(f"Tower_{t_idx}", pos=(1, list(coverage.keys()).index(t_idx)), color='grey')

        # Add the edges
        for t_idx in selected:  # Iterate over selected tower indices
            if t_idx <= t:
                for r in coverage[t_idx]:
                    if selected[t_idx].x == 1:
                        G.add_edge(f"Tower_{t_idx}", f"Region_{r}", color='blue', weight=2)
                    else:
                        G.add_edge(f"Tower_{t_idx}", f"Region_{r}", color='grey', weight=0.1)

        frames.append(G)

    return frames

def update(frame):
    """
    Update function for the animation.
    """
    plt.clf()
    pos = nx.get_node_attributes(frame, 'pos')
    nodes_color = [frame.nodes[n].get('color', 'grey') for n in frame.nodes()]
    edges_color = nx.get_edge_attributes(frame, 'color')
    edges_weight = nx.get_edge_attributes(frame, 'weight')
    max_length = max([len(n) for n in frame.nodes()])
    nx.draw(frame, pos, with_labels=True, node_color=nodes_color, edge_color=list(edges_color.values()),
            edgecolors='grey', node_size=max_length*100, font_size=8, font_color='black', font_weight='bold')
    nx.draw_networkx_edges(frame, pos, edge_color=list(edges_color.values()), width=list(edges_weight.values()))

def extract_data_for_visualization():
    """
    Extract data for comparative analysis visualization.
    """
    coverage = None
    region = None
    selected = None
    covered = None

    # Extract coverage data
    for var in globals():
        if isinstance(globals()[var], dict) and len(globals()[var]) > 0 and isinstance(list(globals()[var].values())[0], set):
            coverage = globals()[var]
            break

    # Extract regions data
    max_len = 0
    for var in globals():
        if isinstance(globals()[var], list) and len(globals()[var]) > max_len:
            region = globals()[var]
            max_len = len(globals()[var])

    # Extract selected towers data
    for var in globals():
        if isinstance(globals()[var], gp.tupledict) and len(globals()[var]) > 0 and set(globals()[var].keys()) == set(coverage.keys()):
            selected = globals()[var]
            break

    # Extract covered regions data
    for var in globals():
        if isinstance(globals()[var], gp.tupledict) and len(globals()[var]) > 0 and set(globals()[var].keys()) == set(region):
            covered = globals()[var]
            break

    return coverage, region, selected, covered

def plot_comparative_analysis(coverage, region, selected, covered):
    """
    Plot a comparative analysis based on extracted data.
    """
    # Your visualization code here
    # For example:
    # Plotting the number of covered regions vs. selected towers
    num_covered_regions = len(covered)
    num_selected_towers = len(selected)
    labels = ['Covered Regions', 'Selected Towers']
    values = [num_covered_regions, num_selected_towers]

    plt.bar(labels, values)
    plt.xlabel('Categories')
    plt.ylabel('Counts')
    plt.title('Comparative Analysis')
    plt.show()


def create_voronoi_diagram(coverage, region, selected, covered):
    """
    Create a Voronoi diagram visualization based on tower coverage data.
    """
    # Generate random tower coordinates for demonstration
    np.random.seed(0)  # for reproducibility
    num_towers = 10
    tower_coords = np.random.randint(0, 100, size=(num_towers, 2))

    # Generate Voronoi diagram
    vor = Voronoi(tower_coords)

    # Plot Voronoi diagram
    fig, ax = plt.subplots(figsize=(8, 6))
    voronoi_plot_2d(vor, ax=ax, show_vertices=False)

    # Highlight selected towers
    for tower_index in selected.keys():
        tower = tower_coords[tower_index]
        ax.plot(tower[0], tower[1], 'ro', markersize=8)

    # Highlight covered regions
    for region_index, gurobi_var in covered.items():
        if gurobi_var.x == 1:  # Check if the region is covered
            if region_index in coverage:
                region_vertices = np.array([tower_coords[idx] for idx in coverage[region_index]])
                ax.fill(region_vertices[:, 0], region_vertices[:, 1], color='lightblue', alpha=0.5)

    # Set plot attributes
    ax.set_title('Voronoi Diagram of Towers and Coverage Regions')
    ax.set_xlabel('X')
    ax.set_ylabel('Y')
    ax.grid(True)

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