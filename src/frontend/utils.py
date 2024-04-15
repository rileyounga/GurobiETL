import re
import pandas as pd

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

def parse(expr, sets):
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
        # We need to know which sets are in the expression so we extract all subscripts we want to iterate over
        indexes = re.findall(r"(\w_\w+|\w_\{\w+,\w+\})", expr)
        index = set()
        for idx in indexes:
            if "{" not in idx:
                index.add(idx.split("_")[1])
            else:
                for i in idx.split("_")[1].replace("{", "").replace("}", "").split(","):
                    index.add(i)

        expr = expr.split(operator[0])
        lhs = expr[0].strip()
        rhs = expr[1].strip()

        ret += "("
        # find the sums
        sums = re.findall(r"/sum_(\w)\^(\w)", lhs)
        if len(sums) > 0:
            ret += "gp.quicksum("
        for sum in sums:
            # if we have a sum over some of our subscripts, we remove them from the set
            # so we don't double count them in our final iteration expression
            for idx in index.copy():
                if sum[0] == idx:
                    index.remove(idx)

        # now that we extracted the info from the sums, we can remove them from the lhs
        lhs = re.sub(r"/sum_(\w)\^(\w)", "", lhs)
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

        subscripts = re.findall(r"(\w_\w+|\w_\{\w+,\w+\})", rhs)
        for subscript in subscripts:
            if "{" not in subscript:
                rhs = rhs.replace(subscript, f"{subscript.split('_')[0]}[{subscript.split('_')[1]}]")
            else:
                rhs = rhs.replace(subscript, f"{subscript.split('_')[0]}[{subscript.split('_')[1].replace('{', '').replace('}', '')}]")

        ret += rhs

        ret += ")"

        # For any remaining subscripts, we iterate over the sets
        for key, value in sets.items():
            if value in index:
                ret += f" for {value} in {key}"

    else:
        indexes = re.findall(r"(\w_\w+|\w_\{\w+,\w+\})", expr)
        index = set()
        for idx in indexes:
            if "{" not in idx:
                index.add(idx.split("_")[1])
            else:
                for i in idx.split("_")[1].replace("{", "").replace("}", "").split(","):
                    index.add(i)

        sums = re.findall(r"/sum_(\w)\^(\w)", expr)
        if len(sums) > 0:
            ret += "gp.quicksum("
        for sum in sums:
            for idx in index.copy():
                if sum[0] == idx:
                    index.remove(idx)

        expr = re.sub(r"/sum_(\w)\^(\w)", "", expr)
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

        for key, value in sets.items():
            if value in index:
                ret += f" for {value} in {key}" 

        if len(sums) > 0:
            ret += ")"
        elif len(index) > 0:
            ret += ")"

    return ret

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
