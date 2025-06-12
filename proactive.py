from typing import List
from fmclient import Agent, Session, Holding, Order, OrderSide, OrderType


class ProactiveBot(Agent):

    def __init__(self, account: str, email: str, password: str, marketplace_id: int):
        super().__init__(account, email, password, marketplace_id)
        self.value = 500
        self.market = None
        self.waiting_for_server = False

    def initialised(self):
        for market_id, market in self.markets.items():
            self.market = market

    def order_accepted(self, order: Order):
        self.waiting_for_server = False

    def order_rejected(self, info: dict, order: Order):
        self.waiting_for_server = False

    def received_orders(self, orders: List[Order]):
        my_orders = []
        for o_id, o in Order.all().items():
            if o.mine and o.is_pending:
                my_orders.append(o)

        if len(my_orders) == 0:
            if not self.waiting_for_server:
                order = Order.create_new(self.market)
                order.order_side = OrderSide.SELL
                order.order_type = OrderType.LIMIT
                order.price = self.value
                order.units = 1
                order.ref = "buy"
                self.waiting_for_server = True
                super().send_order(order)

    def received_holdings(self, holdings: Holding):
        pass

    def received_session_info(self, session: Session):
        pass

    def pre_start_tasks(self):
        pass


if __name__ == "__main__":
    bot = ProactiveBot("regular-idol", "nputna@student.unimelb.edu.au", "1082614", 1174)
    bot.run()