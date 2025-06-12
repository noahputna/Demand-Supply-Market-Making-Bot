"""
This is a template for Project 1, Task 1 (Induced demand-supply)
"""

# T010.
import copy
from fmclient import Agent, Holding, OrderSide, Order, OrderType, Session
from typing import List

# Student details
SUBMISSION = {"number": "1082614", "name": "Noah Putna"}

# ------ Add a variable called PROFIT_MARGIN -----
global PROFIT_MARGIN


class DSBot(Agent):
    # ------ Add an extra argument bot_type to the constructor -----
    def __init__(self, account, email, password, marketplace_id, _role, _bot_type):
        super().__init__(account, email, password, marketplace_id, name="DSBot")

        # Set all base variable conditions when bot has been initialised.
        self._public_market = None
        self._private_market = None
        self._role = None
        self.waiting_for_server = False
        self.traded = False
        self._bot_type = None
        self._order_sent = False
        self._my_public_orders = []
        self._current_agent_order = []
        self._number_of_public_orders = 0
        self._reactive_price = 0
        self._agent_processed = 0
        self._price_condition = 0
        self._type_condition = None
        self._order_side_current = None

    def initialised(self):
        # Identifies the markets the bot has connected with.
        for market_id, market in self.markets.items():
            self.inform(f"Market with id {market_id}")
            if market.private_market:
                self._private_market = market
            else:
                self._public_market = market

    def order_accepted(self, order: Order):
        # Order acceptance conditions of proactive bot.
        if order.ref != "Cancel_order":
            self.waiting_for_server = False
            self._number_of_public_orders = 0
            self._my_public_orders.clear()
        elif self._bot_type == 0 and order.ref != "re_order":
            self.waiting_for_server = False
            self._order_sent = True
            self._agent_processed -= 1
            self._number_of_public_orders += 1
            self._my_public_orders.append(order.fm_id)
        elif self._bot_type == 0:
            self.waiting_for_server = False
            self._order_sent = False
            self._my_public_orders = 0
            self._my_public_orders.clear()

        # Order acceptance conditions of reactive bot.
        if self._bot_type == 1 and order.ref != "re_order":
            self.traded = False
            self.waiting_for_server = False
            self._order_sent = True
            self._agent_processed -= 1
        elif self._bot_type == 1:
            self.traded = False
            self.waiting_for_server = False
            self._order_sent = False

        # Inform observer that order has been accepted.
        self.inform(f"Order accepted {order.ref}")

    def order_rejected(self, info, order: Order):
        # Order rejected conditions of proactive bot.
        if self._bot_type == 0:
            self.waiting_for_server = False

        # Order rejected conditions of reactive bot.
        if self._bot_type == 1:
            self.traded = False
            self.waiting_for_server = False

        # Inform observer that order has been rejected
        self.inform(f"Order rejected {order.ref}")

    def received_orders(self, orders: List[Order]):

        # Proactive bot initialisation.
        if self._bot_type == 0:
            try:

                # If agent order is cancelled clear agent order list.
                for o_id, o in Order.all().items():
                    if o.is_cancelled and o.owner_or_target == "M000":

                        # Cancel all current public orders when agent order has been cancelled
                        for order_id, order in Order.current().items():
                            if order.is_pending and order.mine:
                                # Fulfills the order cancellation of public order.
                                cancel_order: Order = copy.copy(order)
                                cancel_order.order_type = OrderType.CANCEL
                                cancel_order.ref = "Cancel_order"
                                self.waiting_for_server = True
                                super().send_order(cancel_order)
                                self._my_public_orders.clear()

                # Place an order given Agent instructions and desired profit margin.
                for o_id, o in Order.current().items():
                    if o.is_pending and o.owner_or_target == "M000" and o.market.private_market and not o.mine and \
                            o_id not in self._current_agent_order:

                        # Gathers the details of the agent order
                        self._current_agent_order.append(o_id)
                        self._agent_processed = o.units
                        self._price_condition = o.price
                        self._order_side_current = o.order_side
                        self._type_condition = o.order_type

                        # Place order in public market using specifications from the Agent.
                        if not self.waiting_for_server and self._number_of_public_orders == 0 and \
                                self._agent_processed > 0:

                            # Create new order given specifications.
                            order = Order.create_new(self._public_market)
                            order.order_side = self._order_side_current
                            order.order_type = self._type_condition
                            order.units = 1
                            order.ref = "Proactive_order"

                            # Specify order price based on profit margin and agent order conditions.
                            if self._order_side_current == OrderSide.BUY:
                                order.price = self._price_condition - PROFIT_MARGIN
                            else:
                                order.price = self._price_condition + PROFIT_MARGIN

                            # Place the order and wait for server response.
                            self.waiting_for_server = True
                            super().send_order(order)

                # If the order has been traded close out an agent order position and take profit.
                for o_id, o in Order.all().items():
                    if o.has_traded and o.mine and not o.market.private_market and o_id in self._my_public_orders:

                        # Print the profitable trade to notify observer.
                        self._print_trade_opportunity(self._order_side_current, o)

                        # Update role.
                        if self._order_side_current == OrderSide.BUY:
                            self._role = "BUYER"
                        else:
                            self._role = "SELLER"

                        # Clear agent order for convenience.
                        self._current_agent_order.clear()

                        # Place order on the private market to fulfill agent position.
                        re_order = Order.create_new(self._private_market)

                        # Conditions of agent order fulfillment.
                        if self._order_side_current == OrderSide.SELL:
                            re_order.order_side = OrderSide.BUY
                        else:
                            re_order.order_side = OrderSide.SELL

                        # Conditions of agent order fulfillment.
                        re_order.price = self._price_condition
                        re_order.order_type = self._type_condition
                        re_order.units = 1
                        re_order.owner_or_target = "M000"
                        re_order.ref = "re_order"

                        # Place the order and wait for server response.
                        self.waiting_for_server = True
                        super().send_order(re_order)

            except Exception as e:
                self.error(f"{e}")

        # Reactive bot initialisation.
        elif self._bot_type == 1:
            try:

                # Clear Agent order if the order is cancelled in the private market.
                for o_id, o in Order.all().items():
                    if o.is_cancelled and o.owner_or_target == "M000" and o_id in self._current_agent_order:
                        self._current_agent_order.clear()

                # Step through every order which is currently trading.
                for o_id, o in Order.current().items():

                    # If order is a new agent order, save details and set reactive target.
                    if o.is_pending and o.owner_or_target == "M000" and o.market.private_market and not o.mine and \
                            o_id not in self._current_agent_order:

                        # Setting all reactive targets when a new agent order is created.
                        self._current_agent_order.append(o_id)
                        self._agent_processed = o.units
                        self._price_condition = o.price
                        self._order_side_current = o.order_side
                        self._type_condition = o.order_type

                        # Setting reactive price targets based on designated profit margin
                        if o.order_side == OrderSide.BUY:
                            self._reactive_price = o.price - PROFIT_MARGIN
                        elif o.order_side == OrderSide.SELL:
                            self._reactive_price = o.price + PROFIT_MARGIN

                    # If an agent order hasn't been fulfilled yet, pursue active orders on public market
                    if self._agent_processed > 0:

                        # If profit margins are met pursue active order that meets Agent requirement.
                        # Looking for profitable SELL orders.
                        if o.order_side == OrderSide.BUY:
                            if not o.mine and o.is_pending and o.price >= self._reactive_price and \
                                    not o.market.private_market and not self.waiting_for_server:

                                # Print profitable order.
                                self._print_trade_opportunity(self._order_side_current, o)

                                # Update role.
                                self._role = "BUYER"

                                # If order has not been traded yet, react by placing an order.
                                if not self.traded:

                                    # Setting conditions of order to react to currently available order.
                                    order = Order.create_new(self._public_market)
                                    order.order_side = OrderSide.SELL
                                    order.order_type = self._type_condition
                                    order.price = o.price
                                    order.units = 1
                                    order.ref = "Reactive Sell"
                                    self.waiting_for_server = True
                                    self.traded = True
                                    super().send_order(order)

                        # If profit margins are met pursue active order that meets Agent requirement.
                        # Looking for profitable BUY orders.
                        elif o.order_side == OrderSide.SELL:
                            if not o.mine and o.is_pending and o.price <= self._reactive_price and \
                                    not o.market.private_market and not self.waiting_for_server:

                                # Print profitable order.
                                self._print_trade_opportunity(self._order_side_current, o)

                                # Update role.
                                self._role = "SELLER"

                                # If order has not been traded yet, react by placing an order.
                                if not self.traded:

                                    # Setting conditions of order to react to currently available order.
                                    order = Order.create_new(self._public_market)
                                    order.order_side = OrderSide.BUY
                                    order.order_type = self._type_condition
                                    order.price = o.price
                                    order.units = 1
                                    order.ref = "Reactive BUY"
                                    self.waiting_for_server = True
                                    self.traded = True
                                    super().send_order(order)

                    # If an order that we reacted to was completed, we will now profit by completing agent order.
                    # Will continue until Agent order has been completely fulfilled.
                    if self._order_sent is True and not self.waiting_for_server and self._agent_processed >= 0:
                        # Create new private market order.
                        re_order = Order.create_new(self._private_market)

                        # Setting conditions to fulfill agent requirements.
                        re_order.price = self._price_condition
                        re_order.order_type = self._type_condition
                        re_order.units = 1
                        re_order.owner_or_target = "M000"
                        re_order.ref = "re_order"

                        # Sale/purchase condition to fulfill agents requirements.
                        if self._order_side_current == OrderSide.SELL:
                            re_order.order_side = OrderSide.BUY
                        else:
                            re_order.order_side = OrderSide.SELL

                        # Send order based on conditions
                        self.waiting_for_server = True
                        super().send_order(re_order)

            # If an exception occurs it will return a descriptive breakdown of the error.
            # Can be reported to administrator.
            except Exception as e:
                self.error(f"{e}")

    def _print_trade_opportunity(self, role, order):
        # Inform of possible trade opportunity.
        self.inform(f"I am a {role} with profitable order {order}")

    def received_holdings(self, holdings: Holding):
        # Inform of current cash holdings.
        self.inform(f"Cash available is {holdings.cash_available}")
        self.inform(f"Cash settled is {holdings.cash}")

    def received_session_info(self, session: Session):
        # Inform market session information.
        if session.is_open:
            self.inform("Market is open")
        elif session.is_closed:
            self._number_of_public_orders = 0
            self._current_agent_order.clear()
            self._my_public_orders.clear()
            self.inform("Market is closed")
    
    def pre_start_tasks(self):
        # Prompt user will enter a bot type.
        self._bot_type = int(input("Enter a Bot Type: \n"
                                   "PROACTIVE = 0 \n"
                                   "REACTIVE: 1 \n"))

        # Prompt user to enter a profit margin.
        global PROFIT_MARGIN
        PROFIT_MARGIN = int(input("Enter desired profit margin: \n"))


# Launch the bot using personalised trading account.
if __name__ == "__main__":
    FM_ACCOUNT = "regular-idol"
    FM_EMAIL = "nputna@student.unimelb.edu.au"
    FM_PASSWORD = "1082614"
    MARKETPLACE_ID = 1174
    ROLE = 0
    BOT_TYPE = 0

    ds_bot = DSBot(FM_ACCOUNT, FM_EMAIL, FM_PASSWORD, MARKETPLACE_ID, ROLE, BOT_TYPE)
    ds_bot.run()
