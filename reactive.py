"""
Description: This bot monitors buy-side public orders and reacts by selling if the price is higher than a present value.
It demonstrates a basic reative strategy without predicting or initiating trades, only responding to market conditions.

Author: Noah Putna
"""

# -- Import Statments -- 

from typing import List
from fmclient import Agent, Session, Holding, Order, OrderSide, OrderType


class ReactiveBot(Agent):
    """
    A reactive trading bot for Flexemarkets. Handles detection of profitable buy-side orders and reacts by submitting a
    corresponding sell order in the public market. If a public trade occurs, it completes the loop by fulfilling an
    agent instruction in the private market. 

    This illustrates a reactive market-making strategy.
    """

    def __init__(self, account: str, email: str, password: str, marketplace_id: int):
        """ Initialise the Proactive Bot with trading credentials and a fixed sell price. """

        # Initalise instance of Reactive Bot.
        super().__init__(account, email, password, marketplace_id)

        # Initial bot setup values for trading logic.
        self.value = 90
        self.market = None
        self.traded = False
        self.waiting_for_server = False

        # Internal state variables to handle trade tracking and replication.
        self._my_public_orders = []
        self._number_of_public_orders = 0
        self._private_market = None
        self._price_condition = 90 
        self._order_side_current = OrderSide.SELL
        self._type_condition = OrderType.LIMIT


    def initialised(self):
        """ Identify and assign public private markets. """

        for market_id, market in self.markets.items():
            self.market = market

    def order_accepted(self, order: Order):
        """ Mark that an oorder was successfully accepted and trade initiated. """
        self.traded = True

    def order_rejected(self, info: dict, order: Order):
        pass

    def received_orders(self, orders: List[Order]):
        """ React to profitable BUY orders in the public market and fulfill corresponding
        agen request in the private market. """

        for o_id, o in Order.all().items():
            # Look for profitable public BUY orders.
            if not o.mine and o.is_pending and o.order_side == OrderSide.BUY and o.price > self.value:
                if not self.traded:

                    # Create sell order in response.
                    order = Order.create_new(self.market)
                    order.order_side = OrderSide.SELL
                    order.order_type = OrderType.LIMIT
                    order.price = self.value
                    order.units = 1
                    order.ref = "Reactive Sell"
                    super().send_order(order)

                    # Track the order and trade setup.
                    self._my_public_orders.append(order.fm_id)
                    self._price_condition = o.price
                    self._order_side_current = OrderSide.SELL

        # After a successful public trade, fulfill the private agent order.
        for o_id, o in Order.all().items():
            if o.has_traded and o.mine and not o.market.private_market and o_id in self._my_public_orders:

                # Reset internal trackers.
                self._my_public_orders.clear()
                self._number_of_public_orders = 0

                # Create and submit the private market order.
                re_order = Order.create_new(self._private_market)

                # Reverse trade direction for private market execution.
                if self._order_side_current == OrderSide.SELL:
                    re_order.order_side = OrderSide.BUY
                else:
                    re_order.order_side = OrderSide.SELL

                # Set up and send private trade order.
                re_order.price = self._price_condition
                re_order.order_type = self._type_condition
                re_order.units = 1
                re_order.owner_or_target = "M000"
                re_order.ref = "re_order"
                self.waiting_for_server = True
                super().send_order(re_order)

    def received_holdings(self, holdings: Holding):
        pass

    def received_session_info(self, session: Session):
        pass

    def pre_start_tasks(self):
        pass


if __name__ == "__main__":
    """ SECURITY INFORMATION:
    Avoid harcoding credentials - replace FM_EMAIL and FM_PASSWORD with environment variables. """

    FM_EMAIL = "FM_EMAIL" # Replace with environment variable in real use.
    FM_PASSWORD = "FM_PASSWORD" # Replace with environment variable in real use.
    MARKETPLACE_ID = 1174 

    bot = ReactiveBot("regular-idol", FM_EMAIL, FM_PASSWORD, MARKETPLACE_ID)
    bot.run()