"""Token Store page, Terms / Privacy pages and their announcement, and the Statistics day line / rank line.
No network: services.store_service.call is replaced by a recorder that answers like the server."""
import datetime

import pytest

from services import legal_docs, stat_lines, store_service, usage_stats
from tests.test_clipper_overhaul import _pump, window  # noqa: F401  (window is a fixture)

CATALOG = {"currency": "PHP", "packages": [{"tokens": 150, "price_centavos": 1875, "price": "₱18.75"},
                                           {"tokens": 500, "price_centavos": 6250, "price": "₱62.50"},
                                           {"tokens": 1000, "price_centavos": 12500, "price": "₱125.00"}],
           "custom": {"min": 100, "max": 100000, "step": 1}, "rate": {"centavos": 125, "tokens": 10}}


class FakeServer:
    def __init__(self, acks=None, store_ok=True, rank=None, ticket_error=None):
        self.calls, self.acks, self.store_ok, self.rank = [], dict(acks or {}), store_ok, rank
        self.ticket_error = ticket_error

    def __call__(self, method, path, body=None, timeout=None):
        self.calls.append((method, path, body))
        if path == "/api/store":
            return (True, CATALOG, "") if self.store_ok else (False, None, "Couldn't reach CReaper.")
        if path == "/api/store/request":
            if self.ticket_error:
                return False, None, self.ticket_error
            t = body["tokens"]
            price = -(-t * 125 // 10)
            return True, {"reference": "CR-ABCDEFGH", "tokens": t, "price_centavos": price,
                          "price": f"₱{price // 100:,}.{price % 100:02d}", "reused": False, "ticket": "token-12",
                          "thread_url": "https://discord.com/channels/5/77",
                          "thread_app_url": "discord://-/channels/5/77"}, ""
        if path == "/api/policy/acks":
            return True, {"acks": dict(self.acks)}, ""
        if path == "/api/policy/ack":
            self.acks[body["document"]] = body["version"]
            return True, {"ok": True}, ""
        if path == "/api/stats/rank":
            return True, self.rank or {"available": False}, ""
        return False, None, "unknown"


@pytest.fixture
def server(monkeypatch):
    s = FakeServer()
    monkeypatch.setattr(store_service, "call", s)
    return s


def _wait(mgr_threads):
    _pump(3, until=lambda: not any(t.isRunning() for t in list(mgr_threads)))
    _pump(0.2)


# ------------------------------------------------------------------------------------ Token Store
def _open_store(window, premium=True):
    window.account_mgr.account = {"discord_user_id": "111", "tokens": 40, "premium": premium}
    window.main_stack.setCurrentWidget(window.app_widget)
    window.store_mgr.open_store()
    _wait(window.store_mgr._threads)
    return window.store_mgr


def test_the_token_balance_opens_the_store_with_server_prices(window, server):
    st = _open_store(window)
    assert window.view_stack.currentWidget() is window.store_widget
    assert [st.cards[t]["price"].text() for t in (150, 500, 1000)] == ["₱18.75", "₱62.50", "₱125.00"]
    assert "custom" in st.cards and not st.buy_btn.isEnabled()                # nothing chosen yet
    st.select(500)
    assert st.order() == (500, 6250, "") and st.buy_btn.isEnabled() and "₱62.50" in st.order_lbl.text()


def test_prices_show_even_before_the_server_answers_and_buying_stays_server_priced(window, monkeypatch):
    from ui.main_window_store import STORE_DEFAULT
    calls = []

    def offline(method, path, body=None, timeout=None):
        calls.append(path)
        return False, None, "This is being updated right now. Please try again in a few minutes."
    monkeypatch.setattr(store_service, "call", offline)
    st = _open_store(window)
    assert [st.cards[t]["price"].text() for t in (150, 500, 1000)] == ["₱97.50", "₱325.00", "₱650.00"]
    assert not st.premium_box.isHidden() and "available yet" not in st.order_hint.text()
    st.select(500)
    assert st.buy_btn.isEnabled()
    st.buy()
    _wait(st._threads)
    assert "/api/store/request" in calls and st.done_panel.isHidden()          # nothing copied without the server
    assert st.order_hint.text() == "This is being updated right now. Please try again in a few minutes."


def test_the_built_in_prices_match_the_servers_defaults():
    """The table the page opens with must be the server's own default (backend/token_store.py)."""
    import importlib.util
    import os
    from ui.main_window_store import STORE_DEFAULT
    backend = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "backend")
    import sys
    sys.path.insert(0, backend)
    try:
        spec = importlib.util.spec_from_file_location("backend_token_store", os.path.join(backend, "token_store.py"))
        ts = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(ts)
        assert ts.catalog() == STORE_DEFAULT
    finally:
        sys.path.remove(backend)


@pytest.mark.parametrize("text,ok,price", [("100", True, "₱12.50"), ("153", True, "₱19.13"), ("257", True, "₱32.13"),
                                           ("501", True, "₱62.63"), ("12340", True, "₱1,542.50"),
                                           ("90", False, "—"), ("200000", False, "—")])
def test_custom_amounts_show_a_live_price_and_are_validated(window, server, text, ok, price):
    st = _open_store(window)
    st.custom_input.setText(text)
    assert st.selected == "custom" and st.custom_price.text() == price
    assert st.buy_btn.isEnabled() is ok
    shown = st.custom_price.text() + st.order_hint.text() + st.order_lbl.text()
    assert "per 10" not in shown and "10 tokens" not in shown and " = " not in shown   # the formula isn't shown


def test_buy_opens_the_ticket_only_when_the_server_made_it(window, server, monkeypatch):
    st = _open_store(window)
    opened = []
    monkeypatch.setattr(st, "open_ticket", lambda links: opened.append(links))
    st.custom_input.setText("153")
    st.buy()
    st.buy()                                                                     # a double click asks once
    assert st.buy_btn.text() == "Opening your ticket..." and not st.buy_btn.isEnabled()
    _wait(st._threads)
    assert [c for c in server.calls if c[1] == "/api/store/request"] == [("POST", "/api/store/request",
                                                                         {"tokens": 153})]
    assert len(opened) == 1 and opened[0]["thread_app_url"] == "discord://-/channels/5/77"
    assert not st.done_panel.isHidden() and "token-12" in st.done_title.text()
    assert "₱19.13" in st.done_ref.text() and st.buy_btn.isEnabled()


@pytest.mark.parametrize("error", ["We couldn't open your purchase ticket right now. Please try again in a moment.",
                                   "Join the CReaper Discord server with this Discord account first, then try again."])
def test_a_failed_ticket_never_sends_the_user_anywhere(window, monkeypatch, error):
    monkeypatch.setattr(store_service, "call", FakeServer(ticket_error=error))
    st = _open_store(window)
    opened = []
    monkeypatch.setattr(st, "open_ticket", lambda links: opened.append(links))
    st.select(500)
    st.buy()
    _wait(st._threads)
    assert opened == [] and st.done_panel.isHidden()
    assert st.order_hint.text() == error and st.order_hint.property("error") is True


def test_the_ticket_opens_in_discord_or_the_browser(window, monkeypatch):
    import ui.main_window_account as acc
    import ui.main_window_store as store
    st = window.store_mgr
    got = []
    monkeypatch.setattr(acc, "open_discord_app", lambda url: got.append(("app", url)) or False)
    monkeypatch.setattr(store.QDesktopServices, "openUrl", lambda url: got.append(("web", url.toString())))
    st.open_ticket({"thread_app_url": "discord://-/channels/5/77", "thread_url": "https://discord.com/channels/5/77"})
    assert got == [("app", "discord://-/channels/5/77"), ("web", "https://discord.com/channels/5/77")]


def test_non_premium_accounts_get_the_premium_page(window, server, monkeypatch):
    from PyQt6.QtWidgets import QLabel
    window.account_mgr.account = {"discord_user_id": "111", "tokens": 0, "premium": False}
    window.main_stack.setCurrentWidget(window.app_widget)
    window.store_mgr.open_from_balance()
    _pump(0.5)
    assert window.view_stack.currentWidget() is window.premium_widget
    window.store_mgr.open_store()                                               # no way around it
    _pump(0.3)
    assert window.view_stack.currentWidget() is window.premium_widget
    texts = " ".join(l.text() for l in window.premium_widget.findChildren(QLabel))
    # since the plans launch (2026-11-18) the page shows Essential's allowance (backend token_store.premium())
    for must in ("600", "30 days", "₱249", "Auto Clipper", "AI Best Moments", "Token Store", "@adrian or @Mark"):
        assert must in texts
    went = []
    monkeypatch.setattr(window.account_mgr, "open_purchase", lambda: went.append(1))
    window.premium_mgr.buy_btn.click()
    assert went == [1]


def test_the_token_balance_glows_on_hover(window):
    from PyQt6.QtCore import Qt
    chip = window.token_chip
    assert chip.testAttribute(Qt.WidgetAttribute.WA_Hover)
    _obj, anim, glow = chip._hover_glow
    assert glow.blurRadius() == 0.0 and anim.duration() <= 250


def test_the_store_states_the_safety_and_optional_notices(window, server):
    from PyQt6.QtWidgets import QLabel
    st = _open_store(window)
    texts = " ".join(l.text() for l in window.store_widget.findChildren(QLabel))
    for must in ("@adrian and @Mark", "not guaranteed to be recoverable", "only after staff confirm your payment",
                 "Buying tokens is completely optional."):
        assert must in texts


# ------------------------------------------------------------------------------------ Terms / Privacy pages
def test_the_legal_pages_are_in_the_rail_and_readable(window):
    from PyQt6.QtWidgets import QLabel
    window.main_stack.setCurrentWidget(window.app_widget)
    window.terms_btn.click()
    _pump(0.4)
    assert window.view_stack.currentWidget() is window.legal_mgr.pages["terms"] and window.terms_btn.isChecked()
    terms = " ".join(l.text() for l in window.legal_mgr.pages["terms"].findChildren(QLabel))
    for must in ("Essential, Plus and Elite", "2,300 tokens every 72 hours", "7-day refund if unused", "Consumer Act",
                 "@adrian and @Mark", "PayMongo", "at least 13", "Republic of the Philippines"):
        assert must in terms
    window.privacy_btn.click()
    _pump(0.4)
    privacy = " ".join(l.text() for l in window.legal_mgr.pages["privacy"].findChildren(QLabel))
    for must in ("identify", "SHA-256", "48 hours", "third-party AI service providers", "do not sell", "10173",
                 "speech audio", "within 30 minutes", "hashed copy of your password"):
        assert must in privacy
    for internal in ("Groq", "Gemini", "OpenRouter", "Supabase", "Railway", "Cloudflare", "On this PC", "AI-enhanced"):
        assert internal not in privacy + terms                                  # users see CReaper, not its insides
    assert window.privacy_btn.isChecked() and not window.terms_btn.isChecked()


# ------------------------------------------------------------------------------------ the announcement
def _sign_in(window, uid="111"):
    window.account_mgr.account = {"discord_user_id": uid, "tokens": 50}
    window.legal_mgr._asked_for = None
    window.legal_mgr.check_announcement()
    _wait(window.legal_mgr._threads)


def test_existing_users_are_asked_once_and_it_persists_across_restarts(window, server, monkeypatch):
    asked = []
    monkeypatch.setattr("ui.components.policy_notice.show_notice", lambda *a, **k: asked.append(a[1]) or "ok")
    _sign_in(window)
    _wait(window.legal_mgr._threads)
    assert asked == ["We've introduced our Terms of Service and Privacy Policy."]
    assert server.acks == {"terms": legal_docs.TERMS_VERSION, "privacy": legal_docs.PRIVACY_VERSION}
    assert window.settings.get_value("policy_acks")["111"] == server.acks
    _sign_in(window)                                       # a restart / new sign-in: already acknowledged
    window.settings.set_value("policy_acks", {})           # even on a new PC: the account's server record counts
    _sign_in(window)
    assert len(asked) == 1


def test_the_notice_cannot_be_dismissed_by_accident_and_labels_fit(window):
    from PyQt6.QtCore import QEvent, QPointF, Qt
    from PyQt6.QtGui import QMouseEvent
    from ui.components.policy_notice import PolicyNotice
    import ui.main_window_legal as legal
    d = PolicyNotice(window, legal.TITLE, legal.TEXT, "v1", "v2")
    d.show()
    _pump(0.3)
    d.mousePressEvent(QMouseEvent(QEvent.Type.MouseButtonPress, QPointF(2, 2), QPointF(2, 2),
                                  Qt.MouseButton.LeftButton, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier))
    d.reject()                                                                 # Esc / window close
    _pump(0.2)
    assert d.isVisible() and d.choice is None
    for b in (*d.links.values(), d.ok_btn):                                    # nothing cut off
        for lab in b.findChildren(type(d.title_lbl)) or []:
            assert lab.fontMetrics().horizontalAdvance(lab.text()) <= lab.width() + 1
        if not b.findChildren(type(d.title_lbl)):
            assert b.fontMetrics().horizontalAdvance(b.text()) <= b.width()
    d.links["terms"].click()
    assert d.choice == "terms" and not d.isVisible()


def test_viewing_records_nothing(window, server, monkeypatch):
    monkeypatch.setattr("ui.components.policy_notice.show_notice", lambda *a, **k: "privacy")
    _sign_in(window)
    assert server.acks == {} and window.legal_mgr.pending == ["terms", "privacy"]
    assert window.view_stack.currentWidget() is window.legal_mgr.pages["privacy"]
    assert not window.legal_mgr.ack_bars["privacy"].isHidden()               # confirm from the page itself
    _sign_in(window)                                       # next launch: still not acknowledged, asked again
    assert server.acks == {} and window.legal_mgr.pending


def test_a_new_policy_version_asks_again(window, server, monkeypatch):
    import ui.main_window_legal as legal
    asked = []
    monkeypatch.setattr("ui.components.policy_notice.show_notice", lambda *a, **k: asked.append(1) or "ok")
    _sign_in(window)
    monkeypatch.setitem(legal.CURRENT, "privacy", "2027-01-01")
    _sign_in(window)
    assert len(asked) == 2 and server.acks["privacy"] == "2027-01-01"
    assert server.acks["terms"] == legal_docs.TERMS_VERSION


def test_an_offline_acknowledgement_reaches_the_server_later(window, monkeypatch):
    import ui.main_window_legal as legal
    window.settings.set_value("policy_acks", {"111": dict(legal.CURRENT)})
    s = FakeServer()
    monkeypatch.setattr(store_service, "call", s)
    monkeypatch.setattr("ui.components.policy_notice.show_notice", lambda *a, **k: pytest.fail("already acknowledged"))
    _sign_in(window)
    _wait(window.legal_mgr._threads)
    assert s.acks == legal.CURRENT


# ------------------------------------------------------------------------------------ Statistics lines
def test_the_day_line_uses_real_numbers_and_is_stable_per_day():
    st = usage_stats.compute([])
    st.update(events=40, clips_total=137, current_streak=4, videos_processed=12)
    d = datetime.date(2026, 11, 7)
    a = stat_lines.daily_line(st, "u1", d)
    assert a and a == stat_lines.daily_line(st, "u1", d)
    lines = {stat_lines.daily_line(st, "u1", d + datetime.timedelta(days=i)) for i in range(14)}
    assert len(lines) > 1                                                        # it changes over days
    empty = stat_lines.daily_line(usage_stats.compute([]), "u1", d)
    assert empty and not any(ch.isdigit() for ch in empty)                       # no numbers invented


def test_the_rank_line_only_comes_from_the_server():
    assert stat_lines.rank_line(None) == "" and stat_lines.rank_line({"available": False}) == ""
    one = stat_lines.rank_line({"available": True, "rank": 1, "accounts": 80, "count": 312})
    assert "#1" in one and "312 completed runs" in one
    assert "#14 of 80" in stat_lines.rank_line({"available": True, "rank": 14, "accounts": 80, "count": 9})


def test_the_statistics_page_shows_the_line_and_hides_a_missing_rank(window, server):
    from PyQt6.QtWidgets import QLabel
    window.main_stack.setCurrentWidget(window.app_widget)
    window.statistics_mgr.open_statistics()
    _pump(1, until=lambda: getattr(window.statistics_mgr, "_rank", None) is not None)
    texts = " ".join(l.text() for l in window.statistics_widget.findChildren(QLabel))
    assert "Counted from" not in texts
    assert window.statistics_mgr.vibe_lbl.text()
    assert window.statistics_mgr.rank_box.isHidden()                             # no reliable rank: no line


def test_the_thank_you_names_only_real_numbers():
    d = datetime.date(2026, 11, 7)
    st = usage_stats.compute([{"kind": "clipper", "t": 1_790_000_000, "clips": 12, "source": "a", "ai": True}])
    t = stat_lines.thanks_line(st, "u1", d)
    assert t.startswith("Thanks for 12 clips, 1 video and 1 active day with CReaper.") and "unlocked out of 41" in t
    assert t == stat_lines.thanks_line(st, "u1", d)                               # stable all day
    empty = usage_stats.compute([])
    assert "first clip" in stat_lines.thanks_line(empty, "u1", d) and stat_lines.kicker(empty) == "WELCOME TO CREAPER"
    trims = usage_stats.compute([{"kind": "trim", "t": 1_790_000_000, "seconds": 5, "source": "x"}])
    assert "0 clips" not in stat_lines.thanks_line(trims, "u1", d)                # never a zero


def test_the_statistics_page_opens_fully_drawn_and_does_not_rebuild_for_nothing(window, server, monkeypatch):
    from ui.main_window_statistics import AchievementTile
    mgr = window.statistics_mgr
    window.main_stack.setCurrentWidget(window.app_widget)
    usage_stats.record("clipper", clips=3, source="s", aspect="9:16", ai=True)
    mgr.prewarm()                                                                # built off screen
    _pump(1.5, until=lambda: not mgr._queue)
    painted = {k: lab.pixmap().cacheKey() for k, lab in mgr._thumb_labels.items()}
    assert painted and not window.statistics_widget.isVisible()
    mgr.open_statistics()
    assert mgr._queue == [] and all(not lab.pixmap().isNull() for lab in mgr._thumb_labels.values())
    assert {k: lab.pixmap().cacheKey() for k, lab in mgr._thumb_labels.items()} == painted   # reused, not repainted
    builds = []
    monkeypatch.setattr(mgr, "render_page", lambda: builds.append(1))
    mgr._server = {"x": {"id": "x"}}
    mgr._on_server_state(True, "", {"rewards": [{"id": "x"}]})                    # the same answer
    assert builds == []
    mgr._on_server_state(True, "", {"rewards": [{"id": "x", "claimed": True}]})   # a change
    assert builds == []                                                          # updated in place, never rebuilt
    assert window.statistics_widget.findChildren(AchievementTile)


def test_claiming_updates_only_that_tile_and_never_rebuilds_the_page(window, server, monkeypatch):
    from ui.main_window_statistics import AchievementTile
    mgr = window.statistics_mgr
    window.main_stack.setCurrentWidget(window.app_widget)
    usage_stats.set_account("claimer")
    usage_stats.record("clipper", clips=3, source="s", aspect="9:16", ai=True)
    mgr.prewarm()
    _pump(1.0, until=lambda: not mgr._queue)
    mgr.open_statistics()
    tiles = dict(mgr._ach_tiles)
    pick = next(a for a in mgr._ctx["ach"] if a["reward"])
    pick["unlocked"], pick["claimed"] = True, False
    aid = pick["id"]
    mgr._ctx["premium"] = True
    mgr._server = {a["id"]: {"id": a["id"], "verified": True} for a in mgr._ctx["ach"]}
    mgr._sync_achievements()
    assert tiles[aid].state == "claim"
    builds = []
    monkeypatch.setattr(mgr, "render_page", lambda: builds.append(1))
    monkeypatch.setattr(mgr, "request_server_state", lambda force=False: None)
    monkeypatch.setattr(window.account_mgr, "claim_achievement",
                        lambda a, done: done(True, "", {"amount": 5, "already_claimed": False}))
    others = {k: t.state for k, t in tiles.items() if k != aid}
    mgr.claim(aid)
    assert tiles[aid].state == "claimed" and builds == []
    assert dict(mgr._ach_tiles) == tiles and all(mgr._ach_tiles[k] is t for k, t in tiles.items())   # same widgets
    assert {k: t.state for k, t in tiles.items() if k != aid} == others
    assert aid in usage_stats.claimed_ids()


def test_a_claim_is_not_new_activity(window, server):
    usage_stats.set_account("claimer2")
    before = usage_stats.version()
    usage_stats.mark_claimed("first_blood")
    assert "first_blood" in usage_stats.claimed_ids() and usage_stats.version() == before                                      # the page's rebuild key is unchanged


def test_the_note_is_compact_and_built_from_real_numbers(window, server):
    window.main_stack.setCurrentWidget(window.app_widget)
    window.statistics_mgr.open_statistics()
    shout = window.statistics_widget.findChild(type(window.statistics_mgr.rank_box), "statsShout")
    assert shout is not None and shout.sizePolicy().verticalPolicy().name == "Maximum"


def test_notes_never_praise_what_was_not_done():
    import datetime
    d = datetime.date(2026, 11, 7)
    fresh = usage_stats.compute([])
    for i in range(30):
        line = stat_lines.daily_line(fresh, "u", d + datetime.timedelta(days=i))
        assert line and not any(w in line for w in ("streak", "week", "reached", "achievement", "clips"))
    st = usage_stats.compute([{"kind": "clipper", "t": 1_790_000_000, "clips": 2, "source": "a", "ai": True}])
    st.update(clips_7d=0, clips_prev_7d=0, has_prev_week=True, current_streak=0, longest_streak=1)
    for i in range(60):
        line = stat_lines.daily_line(st, "u", d + datetime.timedelta(days=i))
        assert "streak" not in line.lower() and "this week" not in line and "last week" not in line, line
    up = dict(st, clips_7d=12, clips_prev_7d=9, has_prev_week=True)
    seen = {stat_lines.daily_line(up, "u", d + datetime.timedelta(days=i)) for i in range(40)}
    assert any("Three more clips than last week" in l for l in seen) and len(seen) >= 4
    first_week = dict(up, has_prev_week=False)                                  # nothing before tracking to compare with
    assert not any("last week" in stat_lines.daily_line(first_week, "u", d + datetime.timedelta(days=i)) for i in range(40))
    day = stat_lines.daily_line(up, "u", d)
    assert day == stat_lines.daily_line(up, "u", d)                             # stable through the day


def test_the_balance_counts_up_only_when_it_rises(window, monkeypatch):
    import ui.components.token_counter as tc
    monkeypatch.setattr(tc, "reduced_motion", lambda: False)
    from ui.components.token_counter import TokenCounter
    from PyQt6.QtWidgets import QLabel
    lbl = QLabel("0")
    lbl.show()
    c = TokenCounter(lbl)
    c.show(100, "a")
    assert lbl.text() == "100" and not c.animating                              # first value: set directly
    c.show(100, "a")
    assert not c.animating                                                       # same balance: nothing replays
    c.show(60, "a")
    assert lbl.text() == "60" and not c.animating                                # spending: direct
    c.show(2360, "a")
    assert c.animating and c.value < 2360                                        # rising: counts up from the old value
    _pump(4.0, until=lambda: not c.animating)
    assert lbl.text() == "2,360" and not c.animating
    c.show(9999, "b")
    assert lbl.text() == "9,999" and not c.animating                             # another account: never animated


def test_the_store_shows_premium_and_fills_every_card(window, monkeypatch):
    from PyQt6.QtWidgets import QLabel
    cat = dict(CATALOG, premium={"price_centavos": 24900, "price": "₱249.00", "period": "month", "tokens": 2300,
                                 "refill_hours": 72})
    s = FakeServer()
    monkeypatch.setattr(store_service, "call", lambda m, p, b=None, timeout=None: (True, cat, "") if p == "/api/store"
                        else s(m, p, b))
    st = _open_store(window)
    assert not st.premium_box.isHidden() and "2,300 tokens, refilled every 3 days" == st.premium_lbl.text()
    assert "₱249.00" in st.premium_price.text()
    texts = [l.text() for l in st.cards[150]["btn"].findChildren(QLabel)]
    assert "A quick top-up to finish what you started." in texts
    assert not any("min of video" in t for t in texts)


def test_an_older_build_never_reasks_or_downgrades_a_newer_acknowledgement(window, monkeypatch):
    """The bug behind "the agreement shows on every launch": an installed release and a newer build disagreed on the
    document versions; each saw `!=`, asked again, and overwrote the other's acknowledgement."""
    import ui.main_window_legal as legal
    newer = {d: v + ".9" for d, v in legal.CURRENT.items()}            # acknowledged by a newer build
    window.settings.set_value("policy_acks", {"111": dict(newer)})
    s = FakeServer()
    s.acks = dict(newer)
    monkeypatch.setattr(store_service, "call", s)
    monkeypatch.setattr("ui.components.policy_notice.show_notice", lambda *a, **k: pytest.fail("asked again"))
    _sign_in(window)
    _wait(window.legal_mgr._threads)
    assert window.legal_mgr.pending == [] and s.acks == newer
    assert window.settings.get_value("policy_acks")["111"] == newer
    assert legal.version_key("2026-11-07.2") > legal.version_key("2026-11-07")
    assert legal.version_key("2026-11-10") > legal.version_key("2026-11-07.2")
