import numpy as np
import pandas as pd
import yfinance as yf
import matplotlib.pyplot as plt
import io
import math
from gurobipy import GRB
import gurobipy as gp
from matplotlib.backends.backend_agg import FigureCanvasAgg as FigureCanvas
import base64
import json

def portfolio_model(files):
    """
    Create a gurobi model from the dataframes and data_dict
    :param files: dictionary of dataframes
    :param data_dict: dictionary of data
    :return: None
    """
    # Load the data
    stocks = pd.read_csv(files[0])
    stocks = stocks.iloc[1:, 0].str.upper().str.strip().tolist()
    data = yf.download(stocks, period="2y")
    
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
    ax.set_title('Efficient Frontier')
    
    #Save the image locally #ignore the bitio for a second
    plt.savefig("efficient_frontier.png")
    plt.close()

    return 0, 0

def main():
    response = {}
    files = ["stock_options.csv"]
    result, fig = portfolio_model(files)
    response["result"] = result
    response["fig"] = base64.b64encode(fig).decode()
    print(json.dumps(response))

if __name__ == "__main__":
    main()