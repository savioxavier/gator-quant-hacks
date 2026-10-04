
4. Shift signals by one day to avoid **look-ahead bias**.

## Performance Metrics

The notebook evaluates the strategy using:

• CAGR  
• Sharpe Ratio  
• Maximum Drawdown

Example results:

| Metric | Value |
|------|------|
| CAGR | ~3.2% |
| Sharpe | 0.36 |
| Max Drawdown | -28% |

## Visualization

The notebook plots:

- Yield curve (10Y − 2Y)
- Strategy vs benchmark (TLT)

This makes it easy to visually compare risk and return.

## Technologies Used

- Python
- Pandas
- NumPy
- Matplotlib
- yfinance
- pandas-datareader
- Jupyter Notebook

## Goal

The goal of this notebook is to demonstrate how macroeconomic signals such as the yield curve can be used to build systematic bond allocation strategies.
