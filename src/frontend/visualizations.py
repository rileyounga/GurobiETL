import math
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
import yfinance as yf

from statsmodels.tsa.holtwinters import ExponentialSmoothing


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

def plot_portfolio_forecast(data):
    """
    Plot portfolio forecast based on historical data
    :param data: DataFrame containing historical stock data with Date as index and Close prices
    :return: None
    """
    # Compute portfolio value as the sum of close prices of all stocks
    portfolio_value = data['Close'].sum(axis=1)

    # Prepare data
    portfolio_data = pd.DataFrame(portfolio_value, columns=['Portfolio Value'])
    portfolio_data.index = pd.to_datetime(portfolio_data.index)
    portfolio_data = portfolio_data.resample('ME').mean()

    model = ExponentialSmoothing(portfolio_data, trend='add', seasonal='add', seasonal_periods=12).fit()
    forecast = model.forecast(steps=12)  # Forecast for 12 months ahead

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
    
    return fig
