"""
Description: A flexible bot that supports both Proactive and Reactive trading logic based on private/public market conditions.
This file uses a configurable profit margin and role behaviour system for trading in Flexemarkets simulations.

Note:
- Replace FM_EMAIL and FM_PASSWORD with secure environment variables in production use.
- BotType: 0 = Proactive, 1 = Reactive.

Author: Noah Putna
"""

# -- Import Statments -- 

import copy
import sys
from enum import Enum
from fmclient import Agent, Holding, OrderSide, Order, OrderType, Session
from typing import List

# Global variable to define the minimum profit threshold in cents per trade.
global PROFIT_MARGIN

# -- ENUMS --

# Defines if the agent is acting as a buyer or seller.
class Role(Enum):
    BUYER = 0
    SELLER = 1


# Defines bot trading style (Proactive = initates orders, Reactive = responds to market).
class BotType(Enum):
    PROACTIVE = 0
    REACTIVE = 1

# -- DSBot Class Definition --

class DSBot(Agent):
    """ DSBot: Dynamic Strategy Bot
    Implements both proactive and reactive behaviours for trading in Flexemarkets.
    Uses agent signals from private market to trade in public market with profit margin buffer. """

    def __init__(self, account, email, password, marketplace_id, _role, _bot_type):
        """ Initialise the bot with user credentials, marketplace info, and behaviour mode.

        Arguments:
            - account (str): Account name
            - email (str): Login email.
            - password (str): Account password.
            - marketplace_id (int): Target marketplace ID.
            - _role (int): Trading role (BUYER/SELLER).
            - _bot_type: Strategy mode (0 = Proactive, 1 = Reactive). """

        # Initalise bot and trading strategy.
        super().__init__(account, email, password, marketplace_id, name="DSBot")

        # Market links.
        self._public_market = None
        self._private_market = None

        # Role and strategy.
        self._role = None
        self._bot_type = None   # Determines if the bot is proactive or reactive.

        # Trading state trackers.
        self.waiting_for_server = False
        self.traded = False
        self._not_pending = False
        self._order_sent = False

        # Order tracking.
        self._number_of_public_orders = 0
        self._my_public_orders = []
        self._current_agent_order = []
        self._traded_orders = []
        self._cancelled = []

        # Agent order tracking.
        self._reactive_price = 0
        self._type_condition = None
        self._agent_processed = 0
        self._price_condition = 0
        self._order_side_current = None

    def role(self):
        """ Returns the current trading role (BUYER or SELLER). """
        return self._role

    def initialised(self):
        """ Assigns public/private market references after connection. """

        for market_id, market in self.markets.items():
            self.inform(f"Market with id {market_id}")

            if market.private_market:
                # Save reference to the private market (agent-originated orders).
                self._private_market = market
            else:
                # Save reference to the public market (bot-to-bot speculative trades).
                self._public_market = market

    def order_accepted(self, order: Order):
        """ Handles bot response when an order has been accepted by the market. """

        # Manage open order count based on private/public nature.
        if order.is_private:
            self._number_of_public_orders = 0
        elif not order.is_private:
            self._number_of_public_orders += 1
            self._my_public_orders.append(order.fm_id)

        # Track order cancellations.
        if order.order_type == OrderType.CANCEL:
            self._number_of_public_orders = 0
            self._cancelled.append(order)

        # Reset the state trackers based on bot type.
        if self._bot_type == 0:
            self.waiting_for_server = False
        if self._bot_type == 1 and order.ref != "re_order":
            self.traded = False
            self.waiting_for_server = False
            self._order_sent = True
            self._agent_processed -= 1
        elif self._bot_type == 1:
            self.traded = False
            self.waiting_for_server = False
            self._order_sent = False

        self.inform(f"Order accepted {order.ref}")

    def order_rejected(self, info, order: Order):
        """ Handles logic for rejected orders and resets state accordingly. """

        # Conditions when order has been rejected.
        if self._bot_type == 0:
            self.waiting_for_server = False

        if self._bot_type == 1:
            self.traded = False
            self.waiting_for_server = False

        self.inform(f"Order rejected {order.ref}")

    def received_orders(self, orders: List[Order]):
        """ Core logic for both proactive and reactive strategies.
        Evaluates current orders and determines whether to place new orders or respond to opportunities. """

        # -- REACTIVE STRATEGY -- 
        if self._bot_type == 1:
            try:
                
                # Remove cancelled agent orders from tracking.
                for o_id, o in Order.all().items():
                    if o.is_cancelled and o.owner_or_target == "M000" and o_id in self._current_agent_order:
                        self._current_agent_order.clear()

                # Detect new private agent orders.
                for o_id, o in Order.current().items():
                    if o.is_pending and o.owner_or_target == "M000" and o.market.private_market and not o.mine and \
                            o_id not in self._current_agent_order:
                        self._agent_processed = o.units
                        self._current_agent_order.append(o_id)
                        self._price_condition = o.price
                        self._order_side_current = o.order_side
                        self._type_condition = o.order_type

                        # Set profit threshold for re-selling or buying in public market.
                        if o.order_side == OrderSide.BUY:
                            self._reactive_price = o.price - PROFIT_MARGIN
                        elif o.order_side == OrderSide.SELL:
                            self._reactive_price = o.price + PROFIT_MARGIN

                    # Identify public market orders that meet reactive trade conditions.
                    if self._agent_processed > 0:

                        # Case: agent wants to buy, we try to sell.
                        if o.order_side == OrderSide.BUY:
                            if not o.mine and o.is_pending and o.price >= self._reactive_price and \
                                    not o.market.private_market and not self.waiting_for_server:
                                if not self.traded:
                                    order = Order.create_new(self._public_market)
                                    order.order_side = OrderSide.SELL
                                    order.order_type = self._type_condition
                                    order.price = o.price
                                    order.units = 1
                                    order.ref = "Reactive Sell"
                                    self.waiting_for_server = True
                                    self.traded = True
                                    super().send_order(order)

                        #Case: agent wants to sell, we try to buy.
                        elif o.order_side == OrderSide.SELL:
                            if not o.mine and o.is_pending and o.price <= self._reactive_price and \
                                    not o.market.private_market and not self.waiting_for_server:
                                if not self.traded:
                                    order = Order.create_new(self._public_market)
                                    order.order_side = OrderSide.BUY
                                    order.order_type = self._type_condition
                                    order.price = o.price
                                    order.units = 1
                                    order.ref = "Reactive BUY"
                                    self.waiting_for_server = True
                                    self.traded = True
                                    super().send_order(order)

                    # Once we trade in public market, mirror it back in private.
                    if self._order_sent is True and not self.waiting_for_server and self._agent_processed >= 0:
                        re_order = Order.create_new(self._private_market)
                        re_order.price = self._price_condition
                        
                        # Reverse order side for agent trade.
                        if self._order_side_current == OrderSide.SELL:
                            re_order.order_side = OrderSide.BUY
                        else:
                            re_order.order_side = OrderSide.SELL

                        re_order.order_type = self._type_condition
                        re_order.units = 1
                        re_order.owner_or_target = "M000"
                        re_order.ref = "re_order"
                        self.waiting_for_server = True
                        super().send_order(re_order)

            except Exception as e:
                self.error(f"{e}")

        # -- PROACTIVE STRATEGY --
        elif self._bot_type == 0:
            try:
                
                # If a public order has traded, respond in private market.
                for o_id, o in Order.all().items():
                    if o.has_traded and o.mine and not o.market.private_market:
                        self._my_public_orders.clear()
                        self._traded_orders.append(o)
                        self._number_of_public_orders = 0

                        # Look for matching private market opportunity to fulfill.
                        for order_id, order in Order.all().items():
                            if order.is_pending and order.owner_or_target == "M000" and order.market.private_market:
                                price_condition = order.price
                                type_condition = order.order_type
                                unit_condition = o.units
                                order_side_current = order.order_side

                                # Clear previous agent order if complete.
                                if unit_condition == 1:
                                    self._current_agent_order.clear()

                                if not self.waiting_for_server and self._number_of_public_orders == 0:
                                    re_order = Order.create_new(self._private_market)

                                    if order_side_current == OrderSide.SELL:
                                        re_order.order_side = OrderSide.BUY
                                    else:
                                        re_order.order_side = OrderSide.SELL

                                    re_order.price = price_condition
                                    re_order.order_type = type_condition
                                    re_order.units = 1
                                    re_order.owner_or_target = "M000"
                                    re_order.ref = "re_order"
                                    self.waiting_for_server = True
                                    super().send_order(re_order)

                # Cancel public orders if the agent cancels.
                for o_id, o in Order.all().items():
                    if o.is_cancelled and o.owner_or_target == "M000" and o_id in self._current_agent_order:
                        self._current_agent_order.clear()

                        for order_id, order in Order.all().items():
                            if not self.waiting_for_server and order.mine and order.is_pending:
                                cancel_order: Order = copy.copy(order)
                                cancel_order.order_type = OrderType.CANCEL
                                cancel_order.ref = "Cancel order"
                                super().send_order(cancel_order)
                                self.waiting_for_server = True
                                self._my_public_orders.clear()

                # Main proactive trading logic - places orders in public market.
                for o_id, o in Order.current().items():
                    if o.is_pending and o.owner_or_target == "M000" and o.market.private_market:
                        self._current_agent_order.append(o_id)
                        price_condition = o.price
                        unit_condition = o.units
                        type_condition = o.order_type
                        order_side_current = o.order_side

                        if not self.waiting_for_server and self._number_of_public_orders == 0:
                            order = Order.create_new(self._public_market)
                            order.order_side = order_side_current
                            order.order_type = type_condition

                            # Add or subtract profit margin depending on order direction.
                            if order_side_current == OrderSide.BUY:
                                order.price = price_condition - PROFIT_MARGIN
                            else:
                                order.price = price_condition + PROFIT_MARGIN

                            order.units = 1
                            order.ref = "test"
                            self.waiting_for_server = True
                            super().send_order(order)

            except Exception as e:
                self.error(f"{e}")

    def _print_trade_opportunity(self, other_order):
        """ Logs a potential trade opportunity based on detected market order. """

        # Display the trade opportunity to the console/logs.
        self.inform(f"I am a {self._role()} with profitable order {other_order}")

    def received_holdings(self, holdings: Holding):
        """ Receives and logs the current holdings of the agent, including availiable and settled cash. """

        # Log current financial standing.
        self.inform(f"Cash available is {holdings.cash_available}")
        self.inform(f"Cash settled is {holdings.cash}")

    def received_session_info(self, session: Session):
        """ Responds to market session events (open or close). """

        if session.is_open:
            # Notify that trading has started.
            self.inform("Market is open")
        elif session.is_closed:
            # Reset order tracking on session close.
            self._number_of_public_orders = 0
            self._current_agent_order.clear()
            self._my_public_orders.clear()
            self.inform("Market is closed")

    def reason(self, orders):
        """ Debug method to print the current list of orders. """

        try:
            # Display the orders to the console/logs.
            self.inform(f"Current orders {orders}")
        except Exception as e:
            # Handle logging issues.
            self.error(f"{e}")

    def pre_start_tasks(self):
        """ Prompts the user to configure the bot before runtime.
        Sets the bot type (Proactive or Reactive) and the profit margin to use in trading logic. """

        # Get bot type input from user.
        self._bot_type = int(input("Enter a Bot Type: \n"
                                   "PROACTIVE = 0 \n"
                                   "REACTIVE: 1 \n"))

        # Get desired profit margin input and store as global variable.
        global PROFIT_MARGIN
        PROFIT_MARGIN = int(input("Enter desired profit margin: \n"))

if __name__ == "__main__":
    """ Main entry point of the program.
    Instantiates and runs the trading bot with user-defined credentials and settings.

    SECURITY INFORMATION:
    Avoid harcoding credentials - replace FM_EMAIL and FM_PASSWORD with environment variables. """

    FM_ACCOUNT = "regular-idol"
    FM_EMAIL = "FM_EMAIL"       # Replace with environment variable in real use.
    FM_PASSWORD = "FM_PASSWORD" # Replace with environment variable in real use.
    MARKETPLACE_ID = 1174
    ROLE = 0                    # Role: 0 = BUYER, 1 = SELLER
    BOT_TYPE = 0                # Bot Type: 0 = PROACTIVE, 1 = REACTIVE
    
    # Create an instance of the bot and start execution.
    ds_bot = DSBot(FM_ACCOUNT, FM_EMAIL, FM_PASSWORD, MARKETPLACE_ID, ROLE, BOT_TYPE)
    ds_bot.run()

