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
from PIL import Image
from utils import fig2data

from statsmodels.tsa.holtwinters import ExponentialSmoothing

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

    bubble = plot_portfolio_bubble(std, delta, stocks, x)
    pie = plot_portfolio_pie(stocks, x)
    frontier = plot_efficient_frontier(m, x, delta, std, stocks)
    forecast = plot_portfolio_forecast(data)

    # Ignore below for now, I am just checking how to display the plots
    bubble = fig2data(bubble)
    pie = fig2data(pie)
    frontier = fig2data(frontier)
    forecast = fig2data(forecast)

    # now create an image grid of these plots
    # this is a 2x2 grid #get rid of x and y axis, bring the plots closer together
    fig, ax = plt.subplots(2, 2, figsize=(20, 16))
    ax[0, 0].imshow(bubble)
    ax[0, 0].axis('off')
    ax[0, 0].set_title('Portfolio Bubble Chart')
    ax[0, 1].imshow(pie)
    ax[0, 1].axis('off')
    ax[0, 1].set_title('Portfolio Pie Chart')
    ax[1, 0].imshow(frontier)
    ax[1, 0].axis('off')
    ax[1, 0].set_title('Efficient Frontier')
    ax[1, 1].imshow(forecast)
    ax[1, 1].axis('off')
    ax[1, 1].set_title('Portfolio Forecast')

    fig.tight_layout()
    fig.show()

    # save the image to a byte stream
    img = io.BytesIO()
    FigureCanvas(fig).print_png(img)
    output = img.getvalue()

    return result, output


def plot_efficient_frontier(m, x, delta, std, stocks):
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
    ax.set_title('Efficient Frontier')
    
    return fig

def plot_portfolio_bubble(std, delta, stocks, x):
    """
    Plot Portfolio Bubble Chart
    :param std: numpy array of standard deviations (volatility)
    :param delta: numpy array of expected returns
    :param stocks: list of stock symbols
    :param sizes: numpy array of bubble sizes
    :return: None
    """
    fig, ax = plt.subplots(figsize=(10, 8))

    # Plot bubbles
    sizes=x.X
    sizes*=9000
    ax.scatter(x=std, y=delta, s=sizes, alpha=0.6)

    # Annotate bubbles with stock symbols
    for i, stock in enumerate(stocks):
        ax.annotate(stock, (std[i], delta[i]), ha='center', va='center')

    # Set labels and title
    ax.set_xlabel('Volatility (Standard Deviation)')
    ax.set_ylabel('Expected Return')
    ax.set_title('Portfolio Bubble Chart')

    return fig

# Example usage:
# Assume std, delta, stocks, and sizes are numpy arrays and lists containing relevant data
# std: standard deviations (volatility), delta: expected returns, stocks: stock symbols, sizes: bubble sizes
# Call the function with these parameters
# plot_portfolio_bubble(std, delta, stocks, sizes)


def plot_portfolio_forecast(data):
    """
    Plot portfolio forecast based on historical data
    :param data: DataFrame containing historical stock data with Date as index and Close prices
    :return: None
    """
    # Compute portfolio value as the sum of close prices of all stocks
    portfolio_value = data['Close'].sum(axis=1)

    # Prepare data
    # Data is already time series format, so we can simplify the call
    # portfolio_data = pd.DataFrame({'Date': portfolio_value.index, 'Portfolio Value': portfolio_value})
    portfolio_data = pd.DataFrame(portfolio_value, columns=['Portfolio Value'])

    # Convert Date column to index
    # We need to transform the index to a datetime object
    # portfolio_data.set_index('Date', inplace=True)
    portfolio_data.index = pd.to_datetime(portfolio_data.index)

    # Resample data to monthly frequency
    portfolio_data = portfolio_data.resample('ME').mean()

    # Forecasting
    # We need to include both columns and we can add a seasonal component since we have monthly data
    # model = ExponentialSmoothing(portfolio_data['Portfolio Value'], trend='add').fit()
    model = ExponentialSmoothing(portfolio_data, trend='add', seasonal='add', seasonal_periods=12).fit()
    forecast = model.forecast(steps=12)  # Forecast for 12 months ahead

    # Plots should use matplotlib to work with the frontend
    """
    # Plotting
    fig = go.Figure()

    # Historical data
    fig.add_trace(go.Scatter(x=portfolio_data.index, y=portfolio_data['Portfolio Value'],
                             mode='lines', name='Historical Data'))

    # Forecasted data
    forecast_dates = pd.date_range(start=portfolio_data.index[-1], periods=len(forecast), freq='M')[1:]
    fig.add_trace(go.Scatter(x=forecast_dates, y=forecast,
                             mode='lines', name='Forecast'))

    # Add layout
    fig.update_layout(title='Portfolio Forecast',
                      xaxis_title='Date',
                      yaxis_title='Portfolio Value')

    # Show plot
    fig.show()
    """

    fig, ax = plt.subplots(figsize=(10, 8))
    ax.plot(portfolio_data, label='Historical Data')
    ax.plot(forecast, label='Forecast', linestyle='dashed')
    ax.set_xlabel('Date')
    ax.set_ylabel('Portfolio Value')
    ax.set_title('Portfolio Forecast')
    ax.legend()

    return fig


def plot_portfolio_pie(stocks, sizes):
    """
    Plot Portfolio Pie Chart
    :param stocks: list of stock symbols
    :param sizes: numpy array of sizes
    :return: None
    """
    # The portfolio composition is already covered in the text output,
    # how about we base it off of portfolio sector type composition?

    info = yf.Ticker(stocks[0]).info
    sectors = {}
    for stock in stocks:
        info = yf.Ticker(stock).info
        sector = info['sector']
        allocation = sizes.X[stocks.index(stock)]
        if sector in sectors:
            sectors[sector] += allocation
        else:
            sectors[sector] = allocation

    fig, ax = plt.subplots(figsize=(10, 8))

    # Plot pie chart
    ax.pie(sectors.values(), labels=sectors.keys(), autopct='%1.1f%%', startangle=140)

    # Set title
    ax.set_title('Portfolio Market Composition')

    return fig
    

# Example usage:
# Assume stocks and sizes are lists and numpy arrays containing relevant data
# stocks: stock symbols, sizes: sizes of the stocks
# Call the function with these parameters
# plot_portfolio_pie(stocks, sizes)


def main():
    response = {}
    files = ["stock_options.csv"]
    result, fig = portfolio_model(files)
    response["result"] = result
    response["fig"] = base64.b64encode(fig).decode()
    print(json.dumps(response))

if __name__ == "__main__":
    main()