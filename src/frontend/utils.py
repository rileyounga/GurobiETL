import re
import numpy as np

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
        ret += "(" #Note that we are starting with an open parenthesis
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
        subscripts = re.findall(r"(\w_\w+|\w_\{[\w\+\-\,]+\})", lhs)  # Modified regex pattern
        for subscript in subscripts:
            if "{" not in subscript:
                lhs = lhs.replace(subscript, f"{subscript.split('_')[0]}[{subscript.split('_')[1]}]")
            else:
                lhs = lhs.replace(subscript, f"{subscript.split('_')[0]}[{subscript.split('_')[1].replace('{', '').replace('}', '')}]")

        # conditional statement check
        conditional = ""
        cond_split = lhs.split("if")
        lhs = cond_split[0].strip()
        if len(cond_split) > 1:
            conditional = cond_split[1].strip()

        ret += lhs

        # Add the sums back in
        for sum in sums:
            ret += f" for {sum[0]} in {sum[1]}"
        # Add the conditional statement back in
        if len(conditional) > 0:
            ret += f" if {conditional}"
        # Add the closing parenthesis
        if len(sums) > 0:
            ret += ")"

        # Change the operator to python syntax
        if operator[0] == "=":
            operator[0] = "=="
        ret += f" {operator[0]} "

        # Check if there is a forall statement
        forall = re.findall(r"/forall_(\w)\^{(\w+)}", rhs)
        rhs = re.sub(r"/forall_(\w)\^{(\w+)}", "", rhs)

        subscripts = re.findall(r"(\w_\w+|\w_\{[\w\+\-\,]+\})", rhs)  # Modified regex pattern
        for subscript in subscripts:
            if "{" not in subscript:
                rhs = rhs.replace(subscript, f"{subscript.split('_')[0]}[{subscript.split('_')[1]}]")
            else:
                rhs = rhs.replace(subscript, f"{subscript.split('_')[0]}[{subscript.split('_')[1].replace('{', '').replace('}', '')}]")

        # Check for a conditional statement and remove it if it exists
        conditional = ""
        cond_split = rhs.split("if")
        rhs = cond_split[0].strip()
        if len(cond_split) > 1:
            conditional = cond_split[1].strip()

        ret += rhs
        # Add the closing parenthesis
        ret += ")"
        
        # Add the forall statement back in
        for f in forall:
            ret += f" for {f[0]} in {f[1]}"
        # Add the conditional statement back in
        if len(conditional) > 0:
            ret += f" if {conditional}"
        

    else:
        # find the sums
        sums = re.findall(r"/sum_(\w)\^{(\w+)}", expr)
        if len(sums) > 0:
            ret += "gp.quicksum(" 
        # now that we extracted the info from the sums, we can remove them
        expr = re.sub(r"/sum_(\w)\^{(\w+)}", "", expr)

        #find the subscripts to replace with array notation
        subscripts = re.findall(r"(\w_\w+|\w_\{[\w\+\-\,]+\})", expr)
        for subscript in subscripts:
            if "{" not in subscript:
                expr = expr.replace(subscript, f"{subscript.split('_')[0]}[{subscript.split('_')[1]}]")
            else:
                expr = expr.replace(subscript, f"{subscript.split('_')[0]}[{subscript.split('_')[1].replace('{', '').replace('}', '')}]")

        # Check for a conditional statement and remove it if it exists  
        conditional = ""
        cond_split = expr.split("if")
        expr = cond_split[0].strip()
        if len(cond_split) > 1:
            conditional = cond_split[1].strip()

        ret += expr

        # Add the sums back in
        for sum in sums:
            ret += f" for {sum[0]} in {sum[1]}"
        # Add the conditional statement back in
        if len(conditional) > 0:
            ret += f" if {conditional}"
        # Add the closing parenthesis
        if len(sums) > 0:
            ret += ")"

    return ret

def typeparse(value):
    """
    Parse the data type of the value
    :param value: value to parse
    :return: parsed value
    """
    #if type is numpy.int64 or numpy.float64, no need to parse
    if type(value) == np.int64 or type(value) == np.float64:
        return value
    # if type is string, check for list, set, or dictionary
    elif type(value) == str:
        # check for list
        if "[" in value:
            ret = []
            for i in value.replace("[", "").replace("]", "").split(","):
                try:
                    i = int(i)
                except:
                    try:
                        i = float(i)
                    except:
                        pass
                ret.append(i)
        # check for set
        elif "{" in value:
            ret = set()
            for i in value.replace("{", "").replace("}", "").split(","):
                try:
                    i = int(i)
                except:
                    try:
                        i = float(i)
                    except:
                        pass
                ret.add(i)
            return ret
        # check for dictionary
        elif "(" in value:
            ret = {}
            for i in value.replace("(", "").replace(")", "").split(","):
                key, val = i.split(":")
                try:
                    key = int(key)
                except:
                    try:
                        key = float(key)
                    except:
                        pass
                try:
                    val = int(val)
                except:
                    try:
                        val = float(val)
                    except:
                        pass
                ret[key] = val
            return ret
    else:
        return value
    
def fig2data(fig):
    """
    Convert a Matplotlib figure to a 4D numpy array with RGBA channels and return it
    :param fig: Matplotlib figure
    :return: 4D numpy array
    """
    # Draw the figure
    fig.canvas.draw()

    # Get the RGBA buffer from the figure
    w, h = fig.canvas.get_width_height()
    buf = np.frombuffer(fig.canvas.tostring_argb(), dtype=np.uint8)
    buf.shape = (h, w, 4)

    # Reorder the channels
    buf = np.roll(buf, 3, axis=2)

    return buf