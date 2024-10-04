import ccxt
from ccxt.base.types import Balances
from typing import Literal, Dict, Any
from datetime import datetime
from pymongo.database import Database
import pandas as pd
from src.core.time import current_datetime
from src.utils.calc import validate_precision
import numpy as np





def getMockCcxt(exchangeType: type[ccxt.okx],
                initial_balance: dict[str, float],
                db: Database,
                *args, **kwargs):

    class MockCcxt(exchangeType):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            self.mock_balance = initial_balance
            self.order_id_counter = 0
            self.now = None
            self.price = None
            self._market_info = self.load_markets()
            
            # MongoDB collection for all orders
            self.orders_collection = db['ccxt/orders']

        def fetch_balance(self, params: Dict[str, Any] = {}) -> Balances:
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
            if symbol not in self._market_info:
                raise ValueError(f'Invalid {symbol=}')
            if order_type not in ['limit', 'market']:
                raise ValueError(f'Invalid {order_type=}')    
            if side not in ['buy', 'sell']:
                raise ValueError(f'Invalid {side=}')
            
            amount_precision = self._market_info[symbol]['precision']['amount']
            if not validate_precision(amount, amount_precision):
                raise ValueError(f'Invalid amount precision ({amount=} {amount_precision=})')
            
            min_amount = self._market_info[symbol]['limits']['amount']['min']
            if amount < self._market_info[symbol]['limits']['amount']['min']:
                raise ValueError(f'{amount=} must be greater than or equal {min_amount}')
            
            if price:
                price_precision = self._market_info[symbol]['precision']['price']
                if not validate_precision(price, price_precision):
                    raise ValueError(f'Invalid amount precision ({price=} {price_precision=})')

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
                'timestamp': current_datetime().timestamp(),
            }
            # Insert the order into MongoDB
            self.orders_collection.insert_one(order)
            self.__tick__(self.price, self.price, self.price)
            return order

        def fetch_order(self, id: str, symbol: str | None = None, params: Dict[str, Any] = {}):
            # Fetch the order from MongoDB
            order = self.orders_collection.find_one({'id': id})
            if order:
                return order
            else:
                raise ccxt.OrderNotFound(f'Order {id} not found')

        def __tick__(self,
                     price_close: float,
                     price_high: float,
                     price_low: float):
            self.price = price_close
            closed_orders = []

            # Fetch open orders from MongoDB
            open_orders = list(self.orders_collection.find({'status': 'open'}))

            for order in open_orders:
                if order['type'] == 'market':
                    order['status'] = 'closed'
                    order['price'] = price_close
                    self._adjust_balance(order, price_close)
                    closed_orders.append(order)
                elif order['type'] == 'limit' and order['side'] == 'buy' and price_low <= order['price']:
                    order['status'] = 'closed'
                    self._adjust_balance(order, order['price'])
                    closed_orders.append(order)
                elif order['type'] == 'limit' and order['side'] == 'sell' and price_high >= order['price']:
                    order['status'] = 'closed'
                    self._adjust_balance(order, order['price'])
                    closed_orders.append(order)

            # Update MongoDB to reflect closed orders
            for order in closed_orders:
                self.orders_collection.update_one({'id': order['id']}, {'$set': order})

        def _get_fee_rate(self, symbol, order_type):
            if order_type == 'market':
                return self._market_info[symbol]['taker']
            else:
                return self._market_info[symbol]['maker']

        def _adjust_balance(self, order, fill_price):
            if order['side'] == 'buy':
                cost = order['amount'] * fill_price
                fee_rate = self._get_fee_rate(order['symbol'], order['type'])

                if self.mock_balance[order['symbol'].split('/')[1]] < cost:
                    raise ccxt.InsufficientFunds(f'Insufficient funds to cover {cost}/'
                                                 f"{self.mock_balance[order['symbol'].split('/')[1]]}"
                                                 f'{order["symbol"].split("/")[1]} ({fill_price=})')
                
                self.mock_balance[order['symbol'].split('/')[1]] -= cost
                self.mock_balance[order['symbol'].split('/')[0]] += order['amount'] * (1 - fee_rate)

            elif order['side'] == 'sell':
                proceeds = order['amount'] * fill_price
                fee_rate = self._get_fee_rate(order['symbol'], order['type'])

                if self.mock_balance[order['symbol'].split('/')[0]] < order['amount']:
                    raise ccxt.InsufficientFunds(f'Insufficient funds to sell {order["amount"]}/'
                                                 f"{self.mock_balance[order['symbol'].split('/')[0]]}"
                                                 f'{order["symbol"].split("/")[0]} ({fill_price=})')

                self.mock_balance[order['symbol'].split('/')[0]] -= order['amount']
                self.mock_balance[order['symbol'].split('/')[1]] += proceeds * (1 - fee_rate)

        def fetch_ohlcv(self, symbol: str, timeframe='1m', since: int | None = None, limit: int | None = None, params: Any = {}):
            if not since:
                since = (current_datetime() - (limit or 100) * pd.to_timedelta(timeframe)) \
                    .timestamp() * 1000
            else:
                limit = limit or 100
                limit = min(limit,
                            int((current_datetime().timestamp() - since / 1000) / \
                                pd.to_timedelta(timeframe).total_seconds()))
            res = super().fetch_ohlcv(symbol=symbol, timeframe=timeframe, since=since,
                                      limit=limit, params=params)
            return res

    return MockCcxt(*args, **kwargs)
