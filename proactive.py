"""
Description: This provides the bot proactive trading functonality - i.e., attempts to place a
SELL limit order at a fixed price whenever it has no other active order. It demonstrates basic
order placement and session handling using the Flexemarkets API client.

Author: Noah Putna
"""

# -- Import Statments --

from typing import List
from fmclient import Agent, Session, Holding, Order, OrderSide, OrderType


class ProactiveBot(Agent):
    """
    A proactive trading bot that always places a SELL limit order at a fixed price when it has 
    no existing pending orders.
    """

    def __init__(self, account: str, email: str, password: str, marketplace_id: int):
        """
        Initialise the Proactive Bot with trading credentials and a fixed sell price.
        """

        # Initalise instance of Proactive Bot.
        super().__init__(account, email, password, marketplace_id)
        self.value = 500
        self.market = None
        self.waiting_for_server = False

    def initialised(self):
        """
        Called when the bot is connected to the marketplace.
        """
        for market_id, market in self.markets.items():
            self.market = market

    def order_accepted(self, order: Order):
        """"
        Called when an order is accepted by the market.
        Resets the wait flag so another order can be placed.
        """"

        self.waiting_for_server = False

    def order_rejected(self, info: dict, order: Order):
        """
        Called when an order is rejected by the market.
        Resets the server wait flag so the bot can retry.
        """

        self.waiting_for_server = False

    def received_orders(self, orders: List[Order]):
        """
        Core trading logic.
        If there are no current pending orders owned by the bot,
        place a new SELL limit order at the fixed price.
        """

        # Current orders.
        my_orders = []

        # Collate all current pending orders that belong to the bot.
        for o_id, o in Order.all().items():
            if o.mine and o.is_pending:
                my_orders.append(o)

        # Only place a new order if none are pending and we aren't waiting for a server response.
        if len(my_orders) == 0:
            if not self.waiting_for_server:
                order = Order.create_new(self.market)
                order.order_side = OrderSide.SELL
                order.order_type = OrderType.LIMIT
                order.price = self.value
                order.units = 1
                order.ref = "sell"
                self.waiting_for_server = True
                super().send_order(order)

    def received_holdings(self, holdings: Holding):
        pass

    def received_session_info(self, session: Session):
        pass

    def pre_start_tasks(self):
        pass


if __name__ == "__main__":
    """
    SECURITY INFORMATION:
    Avoid harcoding credentials - replace FM_EMAIL and FM_PASSWORD with environment variables
    """

    FM_EMAIL = "FM_EMAIL" # Replace with environment variable in real use.
    FM_PASSWORD = "FM_PASSWORD" # Replace with environment variable in real use.

    bot = ProactiveBot("regular-idol", FM_EMAIL, FM_PASSWORD, 1174)
    bot.run()