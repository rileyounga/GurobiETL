import pandas as pd
import re

def parse_data(files):
    """
    Load all of the files. Parse the data by merging the dataframes on any columns in common.
    :param files: list of file names
    :return: dictionary of dataframes
    """
    
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

    return df_dict

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