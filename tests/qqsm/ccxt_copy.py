import ccxt
from ccxt.base.types import Balances
from typing import List, Literal
from datetime import datetime
import ccxt
from ccxt.base.types import Balances
from typing import Literal, Dict, Any
from datetime import datetime
import pandas as pd
from src.core.time import current_datetime



def getMockCcxt(exchangeType: type[ccxt.okx],
                initial_balance: dict[str, float],
                *args, **kwargs):

    class MockCcxt(exchangeType):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            # Initialize the balance with the given initial balance
            self.mock_balance = initial_balance
            self.mock_orders = {}  # Store the orders in a dict for lookup
            self.open_orders = {}
            self.order_id_counter = 0  # Simple counter for generating unique order IDs
            self.now = None
            self.price = None
            self._market_info = self.load_markets()

        def fetch_balance(self, params: Dict[str, Any] = {}) -> Balances:
            # Returns the current balance in the format ccxt uses
            return {
                'free': self.mock_balance,
                'total': self.mock_balance
            }

        def create_order(self, symbol: str,
                         order_type: Literal['limit', 'market'],
                         side: Literal['buy', 'sell'],
                         amount: float,
                         price: None | str | float | int = None,
                         params: Dict[str, Any] = {}):
            # Simulate an order being created
            self.order_id_counter += 1
            order_id = str(self.order_id_counter)
            order = {
                'id': order_id,
                'symbol': symbol,
                'type': order_type,
                'side': side,
                'amount': amount,
                'price': price,
                'status': 'open',
                'timestamp': current_datetime.timestamp(),
            }
            self.mock_orders[order_id] = order
            self.open_orders[order_id] = order
            self.__tick__(self.price, self.price, self.price)
            return order

        def fetch_order(self, id: str, symbol: str | None = None, params: Dict[str, Any] = {}):
            # Fetch an order by ID
            if id in self.mock_orders:
                return self.mock_orders[id]
            else:
                raise ccxt.OrderNotFound(f'Order {id} not found')

        def __tick__(self,
                     price_close: float,
                     price_high: float,
                     price_low: float):
            """
            This method is for simulating price updates and adjusting orders accordingly.
            For simplicity, we'll assume market orders execute immediately, and limit orders
            execute if the price conditions are met.
            """
            self.price = price_close

            closed_orders_id = []

            # Iterate over orders and see if any should be filled based on price action
            for order_id, order in self.open_orders.items():
                if order['status'] == 'open':
                    if order['type'] == 'market':
                        # Market order gets filled immediately at the close price
                        order['status'] = 'closed'
                        order['price'] = price_close
                        self._adjust_balance(order, price_close)
                        closed_orders_id.append(order['id'])
                    elif order['type'] == 'limit' and order['side'] == 'buy' and price_low <= order['price']:
                        # Buy limit order is filled if the price goes low enough
                        order['status'] = 'closed'
                        self._adjust_balance(order, order['price'])
                        closed_orders_id.append(order['id'])
                    elif order['type'] == 'limit' and order['side'] == 'sell' and price_high >= order['price']:
                        # Sell limit order is filled if the price goes high enough
                        order['status'] = 'closed'
                        self._adjust_balance(order, order['price'])
                        closed_orders_id.append(order['id'])
            
            for i in closed_orders_id:
                del self.open_orders[i]


        def _get_fee_rate(self, symbol, order_type):
            # Determine if the order is a maker or taker
            if order_type == 'market':
                return self._market_info[symbol]['taker']
            else:
                return self._market_info[symbol]['maker']


        def _adjust_balance(self, order, fill_price):
            """
            Adjusts the balance based on the executed order.
            Settles both taker (market order) and maker (limit order) fees.
            """

            # Calculate the fee based on the transaction
            if order['side'] == 'buy':
                cost = order['amount'] * fill_price
                fee_rate = self._get_fee_rate(order['symbol'], order['type'])
                
                if self.mock_balance[order['symbol'].split('/')[1]] < cost:
                    raise ccxt.InsufficientFunds(f'Insufficient funds to cover {cost}/'
                                                 f"{self.mock_balance[order['symbol'].split('/')[1]]}"
                                                 f'{order["symbol"].split("/")[1]} ({fill_price=})')
                
                self.mock_balance[order['symbol'].split('/')[1]] -= cost  # Subtract from quote currency (e.g., USDT)
                self.mock_balance[order['symbol'].split('/')[0]] += order['amount'] * (1 - fee_rate) # Add to base currency (e.g., BTC)

            elif order['side'] == 'sell':
                proceeds = order['amount'] * fill_price
                fee_rate = self._get_fee_rate(order['symbol'], order['type'])

                # Check if user has enough balance to sell the base currency
                if self.mock_balance[order['symbol'].split('/')[0]] < order['amount']:
                    raise ccxt.InsufficientFunds(f'Insufficient funds to sell {order["amount"]}/'
                                                 f"{self.mock_balance[order['symbol'].split('/')[0]]}"
                                                 f'{order["symbol"].split("/")[0]} ({fill_price=})')

                self.mock_balance[order['symbol'].split('/')[0]] -= order['amount']  # Subtract from base currency (e.g., BTC)
                self.mock_balance[order['symbol'].split('/')[1]] += proceeds * (1 - fee_rate)  # Add net proceeds to quote currency (e.g., USDT)


        def fetch_ohlcv(self, symbol: str, timeframe='1m', since: int | None = None, limit: int | None = None, params: Any = {}) -> List[list]:
            if not since:
                since = (current_datetime - (limit or 100) * pd.to_timedelta(timeframe)) \
                    .timestamp() * 1000
            else:
                limit = limit or 100
                limit = min(limit,
                            int((current_datetime.timestamp() - since / 1000) / \
                                pd.to_timedelta(timeframe).total_seconds()))
            
            # print(dict(symbol=symbol, timeframe=timeframe, since=since, limit=limit, params=params))
            return super().fetch_ohlcv(symbol, timeframe, since, limit, params)

    return MockCcxt(*args, **kwargs)


