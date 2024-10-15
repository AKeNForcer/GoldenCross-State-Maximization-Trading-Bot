# GoldenCross-State-Maximization-Trading-Bot

## 1. Introduction

The **GoldenCross-State-Maximization-Trading-Bot** is a trading bot that uses the Exponential Moving Average (EMA) Golden Cross as its key state indicator. It aggregates the returns of time steps with the same state as the current one. The bot then utilizes these aggregated returns to find the optimal allocation between BTC and USDT that maximizes the geometric average return over time and rebalances the assets in the portfolio.

## 2. Prerequisite

- **Integration Backtest Prerequisites:**
  - [Python](https://www.python.org/downloads/)
  - [Poetry](https://python-poetry.org/)
  - [MongoDB](https://www.mongodb.com/)

- **Live Trading Prerequisites:**
  - [Python](https://www.python.org/downloads/)
  - [Poetry](https://python-poetry.org/)
  - [MongoDB](https://www.mongodb.com/)

    **or**
  - [Docker](https://www.docker.com/)


## 3. Setup

To set up the project, follow the steps below:

1. Clone the repository:
    ```bash
    git clone https://github.com/AKeNForcer/GoldenCross-State-Maximization-Trading-Bot.git
    ```
   
2. Navigate into the project directory:
    ```bash
    cd GoldenCross-State-Maximization-Trading-Bot
    ```

3. Start a Poetry shell:
    ```bash
    poetry shell
    ```

4. Install the project dependencies:
    ```bash
    poetry install
    ```

## 4. Run Integration Backtest

To run the integration backtest:

1. Create a `.env.test` file. You can use the `.env.test.example` as a reference.
2. Edit `backtest/config.py` with your specific configurations.
3. Run the backtest script:
    ```bash
    python integration_backtest.py
    ```

4. After completion, the backtest results will be available in your MongoDB database.

## 5. Live Trading

### To run the bot in live trading mode:

1. Create a `.env` file using the `.env.example` as a reference.
2. Edit `config.py` to set up your live trading configurations.
3. Start the bot:
    ```bash
    python main.py
    ```

### To live trade using Docker:

1. Create a `.env` file using the `.env.example` as a reference.
2. Build and run the Docker containers:
    ```bash
    docker compose up --build -d
    ```

3. To see the logs, run:
    ```bash
    docker compose logs
    ```

