import numpy as np
import pandas as pd
import gurobipy as gp
from gurobipy import GRB
import re

verbose=True
# @Everyone: Try running this code locally and tell me what errors you get.
# my computer knows where my gurobi key is, but I can't easily test where I
# should potentiall put it. 

def parse_data(files):
    """
    Load all of the files. Parse the data by merging the dataframes on any columns in common.
    :param files: list of file names
    :return: dictionary of dataframes
    """
    if len(files) == 0:
        if verbose:
            print("No files to parse")
        raise ValueError("No files to parse")
    
    # Read all the files
    file_list = []
    for file in files:
        data = pd.read_csv(file)
        file_list.append(data)

    column_lists = [] # keeps track of all the columns in the dataframes
    df_dict = {} # return value, dictionary of merged dataframes

    for i, data in enumerate(file_list):
        columns = data.columns.tolist()
        new_columns = 0 # keeps track of the new columns per dataframe
        new_dataframes = [] # queue of new dataframes to merge to avoid modifying the dictionary while iterating

        # check if any of the columns are new
        for c in columns:
            if c not in column_lists:
                column_lists.append(c)
                new_columns += 1

        # if all the columns are new, then create a new dataframe
        # if not, then join the dataframes. The dataframe to join
        # is determined by the column name in common
        if new_columns == len(columns):
            df_dict[i] = data
        else:
            # determine which dataframe to join on
            j = -1
            for value in df_dict.values():
                line = str(value).split('\n')[0].split()
                for word in line:
                    # check if the name of one of the columns is in the columns of the dataframe
                    # TODO currently checks for any column name matches, it should propably only check the first column
                    if word in columns:
                        # Queue changes to avoid modifying the dictionary while iterating
                        new_dataframes.append(value.merge(data, on=word, how="left"))
                        break
                j += 1
            df_dict[i] = new_dataframes[0]
            # remove the old dataframe
            # TODO potential issue: indexing the dict item to delete could cause issues
            del df_dict[j]

    # Strip whitespace from column names
    for value in df_dict.values():
        value.columns = value.columns.str.strip()

    if verbose:
        for key, value in df_dict.items():
            print(key, value, "\n")
        print('-'*10, "Data Parsed", '-'*10, "\n")

    return df_dict

def coverage_model(df_dict, data_dict):
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

    # TODO This solution print is also hard-coded to test functionality.
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


def parse(str):
    """
    Parse the string str to be used in the gurobi model
    :param str: string
    :return: string
    """
    # step 1: replace sum with gp.quicksum
    str = str.replace("sum", "gp.quicksum")
    
    # step 2: replace subscripted set variables with array notation
    # step 2.5: get the set variables
    set_vars = re.findall(r"(\w+_\w+)", str)
    sets = []
    for var in set_vars:
        str = str.replace(var, f"{var.split('_')[0]}[{var.split('_')[1][0]}]")
        Index = var.split('_')[1]
        if Index not in sets:
            sets.append(Index)

    # step 3: add the sets as the quicksum arguements in order of appearance
    # in sets corresponding to the order of appearance in the quicksum
    sum_sets = re.findall(r"gp.quicksum\((.*)\)", str)
    for i in range(len(sum_sets)):
        str = str.replace(sum_sets[i], f"{sum_sets[i]} for {sets[i][0]} in {sets[i]}")
    
    return str


def main():
    files = ["costs.csv", "coverage.csv", "population.csv"]
    data_dict = {"parameters": {"budget": 20},
                 "variables": ["build_Tower", "iscovered_Region"], 
                 "objective": ["sum(iscovered_Region * Population_Region)", "maximize"], 
                 "constraints": ["sum(build_Tower * Cost_Tower) <= budget", 
                                 #"sum(build_Tower >= iscovered_Region)"]}
                 ]}
    
    
    df_dict = parse_data(files)
    coverage_model(df_dict, data_dict)


if __name__ == "__main__":
    main()