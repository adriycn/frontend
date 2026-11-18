"""
Token Store page (view 10, opened from the token balance in the title bar and from "Tokens required").

What it does, and what it never does:
  * Prices are the server's (/api/store). The page opens with STORE_DEFAULT, the same table the server ships
    (backend token_store._DEFAULT), so prices are on screen at once and stay there if the server can't be reached;
    the server's answer replaces it. What a purchase costs is always decided by the server (next point).
  * Any whole amount from the minimum up can be bought. The live price uses the server's rate only to SHOW a total
    (rounded up to the centavo, like the server); the purchase is priced by the server again.
  * Buy Tokens (Premium members only; others see the Premium page, ui/main_window_premium.py) asks the server to open
    a private Discord ticket for the order (backend token_tickets.py). The app goes to the ticket only once the server
    says it is complete; while it works the button is disabled (and the server takes one request per account at a
    time, reusing the open ticket for the same amount). Nothing is credited here: staff credit the order after they
    verify the GCash receipt (backend token_store.credit_purchase).
"""
from PyQt6.QtCore import Qt, QTimer, QUrl
from PyQt6.QtGui import QDesktopServices, QIntValidator
from PyQt6.QtWidgets import (QFrame, QGridLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton, QSizePolicy,
                             QVBoxLayout, QWidget)

BUY_CHANNEL = "#🤝ㆍ𝖡𝖴𝖸"
BUY_CHANNEL_ID = "1553319926029353020"
TICKET_READY = "Your order ticket {ticket} is open in Discord."
TICKET_NEXT = ("Send a screenshot of your GCash receipt in the ticket. Staff will check it and add your tokens. Paid "
               "already? Just wait there: you'll be notified.")
OPTIONAL_TEXT = ("Buying tokens is completely optional. Purchases do not provide priority access, faster processing, "
                 "or special treatment. You're welcome to purchase tokens whenever you need them, but there's no "
                 "requirement to do so.")
SAFETY_POINTS = (
    "Only @adrian and @Mark accept payments for CReaper.",
    "Payments sent to anyone else are not guaranteed to be recoverable.",
    "Tokens are added only after staff confirm your payment. Sending money or a screenshot doesn't add tokens "
    "by itself.",
)
STEPS = (("Choose", "Pick a pack or type any amount."),
         ("Your ticket", "Buy Tokens opens a private order ticket for you in Discord."),
         ("Pay with GCash", "Send the total and post your GCash receipt in the ticket."),
         ("Get tokens", "Staff verify the payment and add your tokens."))


# The server's default store (backend/token_store.py _DEFAULT + premium()). Shown until /api/store answers; keep in sync.
STORE_DEFAULT = {
    "currency": "PHP",
    "packages": [{"tokens": 150, "price_centavos": 9750, "price": "₱97.50"},
                 {"tokens": 500, "price_centavos": 32500, "price": "₱325.00"},
                 {"tokens": 1000, "price_centavos": 65000, "price": "₱650.00"}],
    "custom": {"min": 100, "max": 100000, "step": 1},
    "rate": {"centavos": 650, "tokens": 10},
    # since the plans launch (2026-11-18) the store's Premium entry is Essential (backend token_store.premium())
    "premium": {"price_centavos": 24900, "price": "₱249.00", "period": "month", "tokens": 600, "refill_hours": 720,
                "name": "Essential"},
}
BUY_LABEL = "Buy Tokens   →"
BUSY_LABEL = "Opening your ticket..."
PACK_TAGLINES = {0: "A quick top-up to finish what you started.",
                 1: "Room for a busy week of clipping.",
                 2: "For heavy clipping days and long videos."}


def peso(centavos: int) -> str:
    return f"₱{centavos // 100:,}.{centavos % 100:02d}"


class StoreManager:
    def __init__(self, main_window):
        self.mw = main_window
        import copy
        self.catalog = copy.deepcopy(STORE_DEFAULT)   # replaced by the server's answer (load_catalog)
        self.catalog_from_server = False
        self.selected = None              # tokens (int) or "custom"
        self._threads = set()
        self._busy = False

    # ------------------------------------------------------------------ build
    def build_screen(self):
        ui = self.mw.ui_mgr
        widget, col = ui._scroll_page(max_width=1080)
        self.mw.store_widget = widget
        col.setSpacing(0)
        head = QHBoxLayout()
        txt = QVBoxLayout()
        txt.setSpacing(4)
        h = QLabel("Token Store")
        h.setObjectName("h1")
        sub = QLabel("Ran out before your Premium tokens refill? Top up here and keep clipping.")
        sub.setObjectName("pageSubtitle")
        sub.setWordWrap(True)
        txt.addWidget(h)
        txt.addWidget(sub)
        head.addLayout(txt, 1)
        self.balance_lbl = QLabel("")
        self.balance_lbl.setObjectName("pillAccent")
        head.addWidget(self.balance_lbl, 0, Qt.AlignmentFlag.AlignTop)
        col.addLayout(head)
        col.addSpacing(20)

        # --- CReaper Premium (the plan; packs below are top-ups). From the server's catalog only.
        self.premium_box = QFrame()
        self.premium_box.setObjectName("storePremium")
        pl = QHBoxLayout(self.premium_box)
        pl.setContentsMargins(22, 16, 22, 16)
        pl.setSpacing(18)
        ptxt = QVBoxLayout()
        ptxt.setSpacing(3)
        pk = QLabel("CREAPER PREMIUM")
        pk.setObjectName("storeTag")
        pk.setSizePolicy(QSizePolicy.Policy.Maximum, QSizePolicy.Policy.Fixed)
        self.premium_lbl = QLabel("")
        self.premium_lbl.setObjectName("h2")
        self.premium_sub = QLabel("Token packs are one-time top-ups for when you use up your allowance early. "
                                  "They're added on top of your plan and are never required.")
        self.premium_sub.setObjectName("sectionHint")
        self.premium_sub.setWordWrap(True)
        ptxt.addWidget(pk, 0, Qt.AlignmentFlag.AlignLeft)
        ptxt.addSpacing(4)
        ptxt.addWidget(self.premium_lbl)
        ptxt.addWidget(self.premium_sub)
        pl.addLayout(ptxt, 1)
        self.premium_price = QLabel("")
        self.premium_price.setObjectName("storePremiumPrice")
        pl.addWidget(self.premium_price, 0, Qt.AlignmentFlag.AlignVCenter)
        self.premium_box.hide()
        col.addWidget(self.premium_box)
        col.addSpacing(16)

        # --- the packs
        self.grid = QGridLayout()
        self.grid.setHorizontalSpacing(14)
        self.grid.setVerticalSpacing(14)
        self.cards = {}
        col.addLayout(self.grid)
        col.addSpacing(18)

        # --- the order bar: what you're buying + Buy Tokens
        bar = QFrame()
        bar.setObjectName("sheet")
        bl = QHBoxLayout(bar)
        bl.setContentsMargins(24, 18, 18, 18)
        bl.setSpacing(16)
        sel = QVBoxLayout()
        sel.setSpacing(2)
        k = QLabel("YOUR ORDER")
        k.setObjectName("fieldLabel")
        self.order_lbl = QLabel("Choose a pack")
        self.order_lbl.setObjectName("h2")
        self.order_hint = QLabel("")
        self.order_hint.setObjectName("sectionHint")
        self.order_hint.setWordWrap(True)
        sel.addWidget(k)
        sel.addWidget(self.order_lbl)
        sel.addWidget(self.order_hint)
        bl.addLayout(sel, 1)
        self.buy_btn = QPushButton(BUY_LABEL)
        self.buy_btn.setObjectName("storeBuyBtn")
        self.buy_btn.setMinimumSize(230, 54)
        self.buy_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.buy_btn.clicked.connect(self.buy)
        bl.addWidget(self.buy_btn, 0, Qt.AlignmentFlag.AlignVCenter)
        self.mw.ui_mgr._theme_restyle(self.buy_btn, "storeBuyBtn")
        col.addWidget(bar)
        col.addSpacing(14)

        # --- the copied confirmation (hidden until a message was copied)
        self.done_panel = QFrame()
        self.done_panel.setObjectName("storeSuccess")
        dl = QHBoxLayout(self.done_panel)
        dl.setContentsMargins(22, 18, 18, 18)
        dl.setSpacing(16)
        mark = QLabel("✓")
        mark.setObjectName("storeSuccessMark")
        mark.setFixedSize(40, 40)
        mark.setAlignment(Qt.AlignmentFlag.AlignCenter)
        dl.addWidget(mark, 0, Qt.AlignmentFlag.AlignTop)
        dt = QVBoxLayout()
        dt.setSpacing(4)
        self.done_title = QLabel("")
        self.done_title.setObjectName("storeSuccessText")
        self.done_title.setWordWrap(True)
        self.done_ref = QLabel("")
        self.done_ref.setObjectName("sectionHint")
        self.done_ref.setWordWrap(True)
        self.done_ref.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        dt.addWidget(self.done_title)
        dt.addWidget(self.done_ref)
        dl.addLayout(dt, 1)
        btns = QVBoxLayout()
        btns.setSpacing(8)
        self.open_btn = QPushButton("Open my ticket")
        self.open_btn.setObjectName("tintBtn")
        self.open_btn.setMinimumHeight(40)
        self.open_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.open_btn.clicked.connect(lambda: self.open_ticket(self._ticket))
        btns.addWidget(self.open_btn)
        dl.addLayout(btns, 0)
        self.done_panel.hide()
        col.addWidget(self.done_panel)
        self._ticket = None
        col.addSpacing(26)

        # --- how it works
        how = QLabel("HOW IT WORKS")
        how.setObjectName("fieldLabel")
        col.addWidget(how)
        col.addSpacing(10)
        steps = QHBoxLayout()
        steps.setSpacing(12)
        for i, (title, text) in enumerate(STEPS):
            f = QFrame()
            f.setObjectName("storeStep")
            fl = QVBoxLayout(f)
            fl.setContentsMargins(16, 14, 16, 16)
            fl.setSpacing(4)
            n = QLabel(f"{i + 1:02d}")
            n.setObjectName("storeStepNum")
            t = QLabel(title)
            t.setObjectName("sectionTitle")
            d = QLabel(text)
            d.setObjectName("sectionHint")
            d.setWordWrap(True)
            fl.addWidget(n)
            fl.addWidget(t)
            fl.addWidget(d)
            fl.addStretch(1)
            steps.addWidget(f, 1)
        col.addLayout(steps)
        col.addSpacing(18)

        # --- safety + optional notice
        notes = QHBoxLayout()
        notes.setSpacing(12)
        safe = QFrame()
        safe.setObjectName("storeWarning")
        sl = QVBoxLayout(safe)
        sl.setContentsMargins(20, 16, 20, 18)
        sl.setSpacing(6)
        st = QLabel("Payment safety")
        st.setObjectName("storeWarningTitle")
        sl.addWidget(st)
        for p in SAFETY_POINTS:
            lab = QLabel(f"•  {p}")
            lab.setObjectName("sectionHint")
            lab.setWordWrap(True)
            sl.addWidget(lab)
        notes.addWidget(safe, 3)
        opt = QFrame()
        opt.setObjectName("sheet")
        ol = QVBoxLayout(opt)
        ol.setContentsMargins(20, 16, 20, 18)
        ol.setSpacing(6)
        ot = QLabel("Always optional")
        ot.setObjectName("sectionTitle")
        oo = QLabel(OPTIONAL_TEXT)
        oo.setObjectName("sectionHint")
        oo.setWordWrap(True)
        self.optional_lbl = oo
        ol.addWidget(ot)
        ol.addWidget(oo)
        notes.addWidget(opt, 2)
        col.addLayout(notes)
        col.addStretch(1)
        self.mw.view_stack.addWidget(widget)
        self._render_cards()
        self._update_order()

    # ------------------------------------------------------------------ the cards
    def _card(self, key):
        b = QPushButton()
        b.setObjectName("storeCard")
        b.setCheckable(True)
        b.setCursor(Qt.CursorShape.PointingHandCursor)
        b.setMinimumHeight(250)
        b.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        lay = QVBoxLayout(b)
        lay.setContentsMargins(22, 20, 22, 20)
        lay.setSpacing(0)
        b.clicked.connect(lambda _=False, k=key: self.select(k))
        return b, lay

    @staticmethod
    def _label(text, name, wrap=False):
        lab = QLabel(text)
        lab.setObjectName(name)
        lab.setWordWrap(wrap)
        lab.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        return lab

    def _clear_grid(self):
        while self.grid.count():
            item = self.grid.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        self.cards = {}

    def _render_cards(self):
        from ui.main_window_ui import make_token_badge
        self._clear_grid()
        cat = self.catalog
        packs = cat["packages"]
        best = max((p["tokens"] for p in packs), default=None)
        names = {0: "STARTER", 1: "POPULAR", 2: "BEST VALUE"}
        for i, p in enumerate(packs):
            b, lay = self._card(p["tokens"])
            tag = self._label(names.get(i, "PACK") if len(packs) == 3 else "PACK",
                              "storeTag" if p["tokens"] == best else "fieldLabel")
            tag.setSizePolicy(QSizePolicy.Policy.Maximum, QSizePolicy.Policy.Fixed)
            tag.setFixedHeight(22)                       # pill or plain: every card's amount on the same line
            lay.addWidget(tag, 0, Qt.AlignmentFlag.AlignLeft)
            lay.addSpacing(22)
            chip, _lbl = make_token_badge("", size=26, object_name="storeIcon")
            chip.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
            row = QHBoxLayout()
            row.setSpacing(6)
            row.addWidget(chip, 0, Qt.AlignmentFlag.AlignVCenter)
            row.addWidget(self._label(f"{p['tokens']:,}", "storeAmount"), 0, Qt.AlignmentFlag.AlignVCenter)
            row.addStretch(1)
            lay.addLayout(row)
            lay.addWidget(self._label("tokens", "storeUnit"))
            lay.addSpacing(14)
            lay.addWidget(self._label(PACK_TAGLINES.get(i, ""), "sectionHint", wrap=True))
            lay.addStretch(1)
            line = QFrame()
            line.setObjectName("storeDivider")
            line.setFixedHeight(1)
            lay.addWidget(line)
            lay.addSpacing(14)
            price = self._label(p["price"], "storePrice")
            lay.addWidget(price)
            self.cards[p["tokens"]] = {"btn": b, "price": price}
            self.grid.addWidget(b, 0, i)
        # custom amount
        b, lay = self._card("custom")
        tag = self._label("CUSTOM", "fieldLabel")
        tag.setFixedHeight(22)
        lay.addWidget(tag, 0, Qt.AlignmentFlag.AlignLeft)
        lay.addSpacing(18)
        self.custom_input = QLineEdit()
        self.custom_input.setObjectName("storeInput")
        self.custom_input.setPlaceholderText("Amount")
        self.custom_input.setMinimumHeight(48)
        lim = cat["custom"]
        self.custom_input.setValidator(QIntValidator(0, int(lim["max"]) * 10))
        self.custom_input.textChanged.connect(self._on_custom)
        self.custom_input.focusInEvent = self._wrap_focus(self.custom_input.focusInEvent)
        lay.addWidget(self.custom_input)
        lay.addSpacing(6)
        lay.addWidget(self._label("tokens", "storeUnit"))
        lay.addSpacing(14)
        self.custom_hint = self._label(f"Any amount from {lim['min']:,} to {lim['max']:,}.", "sectionHint", wrap=True)
        lay.addWidget(self.custom_hint)
        lay.addStretch(1)
        line = QFrame()
        line.setObjectName("storeDivider")
        line.setFixedHeight(1)
        lay.addWidget(line)
        lay.addSpacing(14)
        self.custom_price = QLabel("Enter an amount")
        self.custom_price.setObjectName("storePrice")
        lay.addWidget(self.custom_price)
        self.cards["custom"] = {"btn": b, "price": self.custom_price}
        self.grid.addWidget(b, 0, len(packs))
        for c in range(len(packs) + 1):
            self.grid.setColumnStretch(c, 1)
        if self.selected in self.cards:
            self.cards[self.selected]["btn"].setChecked(True)
        self._show_premium()

    def _show_premium(self):
        prem = self.catalog.get("premium")
        if not prem:
            self.premium_box.hide()
            return
        hours = int(prem.get("refill_hours") or 0)
        every = f"{hours // 24} days" if hours and hours % 24 == 0 else f"{hours} hours"
        self.premium_lbl.setText(f"{int(prem['tokens']):,} tokens, refilled every {every}")
        self.premium_price.setText(f"{prem['price']}<span style='font-size:13px; font-weight:600; color:#A3A3B1'>"
                                   f" / {prem.get('period', 'month')}</span>")
        self.premium_box.show()

    def _wrap_focus(self, original):
        def focus_in(e):
            self.select("custom")
            original(e)
        return focus_in

    # ------------------------------------------------------------------ state
    def is_premium(self) -> bool:
        try:
            return bool((self.mw.account_mgr.account or {}).get("premium"))
        except Exception:
            return False

    def open_from_balance(self):
        """The token balance in the title bar: the Token Store for Premium members, the Premium page for everyone
        else (the server refuses Token Store orders from non-Premium accounts too)."""
        if self.is_premium():
            self.open_store()
        else:
            self.mw.premium_mgr.open_premium()

    def open_store(self):
        if not self.is_premium():
            self.mw.premium_mgr.open_premium()
            return
        from ui.main_window_ui import fade_switch
        self.refresh_balance()
        fade_switch(self.mw.view_stack, self.mw.view_stack.indexOf(self.mw.store_widget))
        if not self.catalog_from_server:
            self.load_catalog()

    def refresh_balance(self):
        try:
            n = int(self.mw.account_mgr.tokens())
            self.balance_lbl.setText(f"Balance  {n:,} tokens")
        except Exception:
            self.balance_lbl.setText("")

    def load_catalog(self):
        from services.store_service import ApiThread
        t = ApiThread("GET", "/api/store")
        t.done.connect(self._on_catalog)
        self._keep(t)

    def _on_catalog(self, ok, data, err):
        if not ok or not isinstance(data, dict) or not data.get("packages") or not data.get("custom"):
            return                                       # the built-in table stays on screen; Buy asks the server
        self.catalog = {**STORE_DEFAULT, **data}
        self.catalog_from_server = True
        self._render_cards()
        self._update_order()

    def select(self, key):
        self.selected = key
        for k, c in self.cards.items():
            c["btn"].setChecked(k == key)
        self._update_order()

    def custom_amount(self):
        try:
            return int(self.custom_input.text().replace(",", "").strip())
        except (ValueError, AttributeError):
            return None

    def custom_error(self, n):
        """Why a custom amount can't be bought ('' = it can), from the server's limits."""
        lim = self.catalog["custom"]
        if n is None:
            return f"Enter {lim['min']:,} to {lim['max']:,} tokens."
        if n < lim["min"]:
            return f"The smallest amount is {lim['min']:,} tokens."
        if n > lim["max"]:
            return f"The largest amount is {lim['max']:,} tokens."
        if lim.get("step", 1) > 1 and n % lim["step"]:
            return f"Choose an amount in steps of {lim['step']}."
        return ""

    def display_price(self, tokens: int):
        """The total to SHOW (the server prices the actual request again)."""
        rate = self.catalog["rate"]
        return -(-int(tokens) * int(rate["centavos"]) // int(rate["tokens"]))      # rounded up, as on the server

    def _on_custom(self, _text=""):
        n = self.custom_amount()
        err = self.custom_error(n)
        if not self.custom_input.text().strip():
            self.custom_price.setText("Enter an amount")
        elif err:
            self.custom_price.setText("—")
        else:
            self.custom_price.setText(peso(self.display_price(n)))
        if self.selected != "custom" and self.custom_input.text().strip():
            self.select("custom")
        else:
            self._update_order()

    def order(self):
        """(tokens, centavos, error)."""
        if self.selected is None:
            return None, None, "Choose a pack or enter your own amount."
        if self.selected == "custom":
            n = self.custom_amount()
            err = self.custom_error(n)
            return (None, None, err) if err else (n, self.display_price(n), "")
        p = next((p for p in self.catalog["packages"] if p["tokens"] == self.selected), None)
        return (p["tokens"], p["price_centavos"], "") if p else (None, None, "Choose a pack.")

    def _update_order(self, error: bool = False):
        tokens, price, err = self.order()
        if tokens:
            self.order_lbl.setText(f"{tokens:,} tokens  ·  {peso(price)}")
            self._hint("Buy Tokens opens a private order ticket for you in Discord.")
        else:
            self.order_lbl.setText("Choose a pack")
            if not error:
                self._hint(err)
        self.buy_btn.setEnabled(bool(tokens) and not self._busy)

    # ------------------------------------------------------------------ buying
    def buy(self):
        tokens, _price, err = self.order()
        if not tokens or self._busy:
            if err:
                self._hint(err, error=True)
            return
        from services.store_service import ApiThread
        self._busy = True
        self.buy_btn.setEnabled(False)
        self.buy_btn.setText(BUSY_LABEL)
        self.done_panel.hide()
        t = ApiThread("POST", "/api/store/request", {"tokens": tokens})
        t.done.connect(self._on_request)
        self._keep(t)

    def _on_request(self, ok, data, err):
        self._busy = False
        self.buy_btn.setText(BUY_LABEL)
        self._update_order()
        links = data if ok and isinstance(data, dict) else {}
        if not (links.get("thread_url") or links.get("thread_app_url")):
            self.done_panel.hide()
            self._hint(err or "We couldn't open your order ticket. Please try again in a moment.", error=True)
            if not ok and "Premium" in str(err):
                self.mw.premium_mgr.open_premium()
            return
        self._ticket = links
        self.done_title.setText(TICKET_READY.format(ticket=links.get("ticket") or ""))
        self.done_ref.setText(f"{TICKET_NEXT}\nOrder {links.get('reference', '')}  ·  {int(links.get('tokens') or 0):,} "
                              f"tokens  ·  {links.get('price', '')}")
        self.done_panel.show()
        self.open_ticket(links)

    def open_ticket(self, links):
        """The ticket in the Discord app when it's installed, otherwise in the browser."""
        if not links:
            return
        from ui.main_window_account import open_discord_app
        if links.get("thread_app_url") and open_discord_app(links["thread_app_url"]):
            return
        if links.get("thread_url"):
            QDesktopServices.openUrl(QUrl(links["thread_url"]))

    def _hint(self, text, error=False):
        self.order_hint.setText(text)
        self.order_hint.setProperty("error", bool(error))
        self.order_hint.style().unpolish(self.order_hint)
        self.order_hint.style().polish(self.order_hint)

    def _keep(self, t):
        self._threads.add(t)
        t.finished.connect(lambda t=t: self._threads.discard(t))
        t.start()

    def shutdown(self):
        for t in list(self._threads):
            t.wait(2000)
