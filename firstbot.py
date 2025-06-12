import copy
from typing import List

from fmclient import Agent, Session, Holding, Order, OrderSide, OrderType


class FirstBot(Agent):

    def __init__(self, account: str, email: str, password: str, marketplace_id: int):
        super().__init__(account, email, password, marketplace_id)
        self.public_market = None
        self.private_market = None
        self.order_sent = False

    def initialised(self):
        for market_id, market in self.markets.items():
            self.inform(f"Market with id {market_id}")
            if market.private_market:
                self.private_market = market
            else:
                self.public_market = market

    def order_accepted(self, order: Order):
        self.inform(f"order accepted {order.ref}")

    def order_rejected(self, info: dict, order: Order):
        self.inform(f"order rejected {order.ref}")

    def received_orders(self, orders: List[Order]):
        try:
            x = 10/0
        except Exception as e:
            self.error(f"{e}")
        # for order_id, order in Order.all().items():
        #     if order.mine:
        #         self.inform(f"This is my order {order}")
        #         if order.is_pending:
        #             self.inform("This order is pending.")

        # if not self.order_sent:
        #     order: Order = Order.create_new(self.private_market)
        #     order.price = 500
        #     order.order_side = OrderSide.BUY
        #     order.order_type = OrderType.LIMIT
        #     order.units = 1
        #     order.ref = "firstorder"
        #     order.owner_or_target = "M000"
        #     super().send_order(order)
        #     self.order_sent = True

        for order_id, order in Order.all().items():
            if order.mine and order.is_pending:
                cancel_order: Order = copy.copy(order)
                cancel_order.order_type = OrderType.CANCEL
                cancel_order.ref = "cancelorder"
                super().send_order(cancel_order)

    def received_holdings(self, holdings: Holding):
        self.inform(f"Cash available is {holdings.cash_available}")
        self.inform(f"Cash settled is {holdings.cash}")

    def received_session_info(self, session: Session):
        if session.is_open:
            self.inform("Market is open")
        elif session.is_closed:
            self.inform("Market is closed")

    def reason(self, order_price):
        """
        This method does ....
        :param order_price: the price of the order to send
        :return:
        """
        self.inform("I will be called every 10s")

    def pre_start_tasks(self):
        self.execute_periodically(self.reason, 10)


if __name__ == "__main__":
    bot = FirstBot("regular-idol", "u10@bmm", "21", 1159)
    bot.run()
