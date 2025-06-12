from typing import List
from fmclient import Agent, Session, Holding, Order, OrderSide, OrderType


class ReactiveBot(Agent):
    for o_id, o in Order.all().items():
        if o.has_traded and o.mine and not o.market.private_market and o_id in self._my_public_orders:
            self._my_public_orders.clear()
            self._number_of_public_orders = 0

            re_order = Order.create_new(self._private_market)

            if self._order_side_current == OrderSide.SELL:
                re_order.order_side = OrderSide.BUY
            else:
                re_order.order_side = OrderSide.SELL

            re_order.price = self._price_condition
            re_order.order_type = self._type_condition
            re_order.units = 1
            re_order.owner_or_target = "M000"
            re_order.ref = "re_order"
            self.waiting_for_server = True
            super().send_order(re_order)

    def __init__(self, account: str, email: str, password: str, marketplace_id: int):
        super().__init__(account, email, password, marketplace_id)
        self.value = 90
        self.market = None
        self.traded = False
        self.waiting_for_server = False

    def initialised(self):
        for market_id, market in self.markets.items():
            self.market = market

    def order_accepted(self, order: Order):
        self.traded = True

    def order_rejected(self, info: dict, order: Order):
        pass

    def received_orders(self, orders: List[Order]):
        for o_id, o in Order.all().items():
            if not o.mine and o.is_pending and o.order_side == OrderSide.BUY and o.price > self.value:
                if not self.traded:
                    order = Order.create_new(self.market)
                    order.order_side = OrderSide.SELL
                    order.order_type = OrderType.LIMIT
                    order.price = self.value
                    order.units = 1
                    order.ref = "buy"
                    super().send_order(order)

    def received_holdings(self, holdings: Holding):
        pass

    def received_session_info(self, session: Session):
        pass

    def pre_start_tasks(self):
        pass


if __name__ == "__main__":
    bot = ReactiveBot("regular-idol", "nputna@student.unimelb.edu.au", "1082614", 1174)
    bot.run()