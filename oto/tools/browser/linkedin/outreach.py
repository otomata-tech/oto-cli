"""LinkedIn outreach mixin: send messages and connection invitations.

Anchors on stable aria-labels / visible button text matched across FR/EN locales
(LinkedIn's CSS classes are hashed and change often). Two primitives:

- send_message: only works for 1st-degree connections (or InMail with a premium
  account). For a cold contact, the "Message" button is absent → raises.
- send_invitation: the cold-outreach primitive — connection request, optional note.

Both support dry_run: perform every step except the final send click, and save a
screenshot, so the flow can be validated without contacting a real person.
"""

import random
from pathlib import Path
from typing import Optional

from ._js import JS_MARK_CONTROL, JS_CLEAR_MARK

# Visible-text / aria-label vocabulary (FR + EN)
_MESSAGE_LABELS = ["message"]
_CONNECT_LABELS = ["se connecter", "connect", "inviter", "invite"]
_MORE_LABELS = ["plus", "more"]
_ADD_NOTE_LABELS = ["ajouter une note", "add a note"]
_SEND_LABELS = ["envoyer", "send"]
_SEND_NO_NOTE_LABELS = ["envoyer sans note", "send without a note"]

# Stable-ish LinkedIn DOM anchors that long predate the SDUI rewrite
_COMPOSE_BOX = 'div.msg-form__contenteditable[contenteditable="true"]'
_MSG_SEND_BUTTON = "button.msg-form__send-button"
_INVITE_NOTE_TEXTAREA = "textarea[name='message'], #custom-message"
_MODAL = "div[role='dialog'], .artdeco-modal"

_NOTE_MAX = 300  # LinkedIn caps connection notes (200 free / 300 premium)


class OutreachMixin:
    """Send LinkedIn messages and connection invitations via browser automation."""

    # --- low-level control helpers ---

    async def _click_control(self, labels, tags=("button", "a"), timeout: float = 8.0) -> str:
        """Find a visible control matching any label, real-click it. Raise if none."""
        deadline = timeout
        marker = None
        while deadline > 0:
            marker = await self.page.evaluate(
                JS_MARK_CONTROL, {"labels": list(labels), "tags": list(tags)}
            )
            if marker:
                break
            await self.wait(0.5)
            deadline -= 0.5
        if not marker:
            raise RuntimeError(
                f"No clickable control matching {labels} found on the page."
            )
        # JS click rather than a Playwright pointer click: LinkedIn buttons wrap
        # an inner <svg> that intercepts pointer events, which makes actionability
        # clicks retry until timeout. el.click() still fires React's handlers.
        await self.page.eval_on_selector(marker, "el => el.click()")
        await self.page.evaluate(JS_CLEAR_MARK)
        await self.wait(random.uniform(0.8, 1.6))
        return marker

    async def _human_type(self, text: str):
        await self.page.keyboard.type(text, delay=random.randint(25, 70))

    # --- messaging (1st-degree only) ---

    async def send_message(self, profile_url: str, message: str, dry_run: bool = False) -> dict:
        """Send a direct message to a 1st-degree connection from their profile."""
        if not message.strip():
            raise ValueError("Message body is empty.")

        await self.check_rate_limit("message")
        await self.goto(profile_url)
        await self._raise_if_auth_wall()
        await self.wait(random.uniform(2.0, 3.5))

        try:
            await self._click_control(_MESSAGE_LABELS, tags=("button", "a"))
        except RuntimeError as e:
            raise RuntimeError(
                "No 'Message' button on this profile — you are likely not a "
                "1st-degree connection (direct messaging requires being connected, "
                "or a premium InMail). Use send_invitation to connect first."
            ) from e

        await self.page.wait_for_selector(_COMPOSE_BOX, timeout=10000)
        await self.page.eval_on_selector(_COMPOSE_BOX, "el => el.focus()")
        await self.wait(random.uniform(0.4, 0.9))
        await self._human_type(message)
        await self.wait(random.uniform(0.6, 1.2))

        if dry_run:
            shot = str(Path("/tmp") / "oto-linkedin-message.png")
            await self.screenshot(shot, full_page=False)
            return {
                "status": "dry_run",
                "action": "message",
                "profile": profile_url,
                "message": message,
                "screenshot": shot,
            }

        send_btn = await self.page.query_selector(_MSG_SEND_BUTTON)
        if send_btn and not await send_btn.is_disabled():
            await self.page.eval_on_selector(_MSG_SEND_BUTTON, "el => el.click()")
        else:
            await self._click_control(_SEND_LABELS, tags=("button",))
        await self.wait(random.uniform(1.5, 2.5))

        return {"status": "sent", "action": "message", "profile": profile_url}

    # --- connection invitation (cold outreach) ---

    async def send_invitation(self, profile_url: str, note: Optional[str] = None,
                              dry_run: bool = False) -> dict:
        """Send a connection request, optionally with a note (<=300 chars)."""
        if note and len(note) > _NOTE_MAX:
            raise ValueError(
                f"Note is {len(note)} chars; LinkedIn caps invitation notes at {_NOTE_MAX}."
            )

        await self.check_rate_limit("invitation")
        await self.goto(profile_url)
        await self._raise_if_auth_wall()
        await self.wait(random.uniform(2.0, 3.5))

        # "Connect" is sometimes a primary action, sometimes hidden under "More".
        try:
            await self._click_control(_CONNECT_LABELS, tags=("button",))
        except RuntimeError:
            await self._click_control(_MORE_LABELS, tags=("button",))
            await self.wait(random.uniform(0.6, 1.2))
            await self._click_control(_CONNECT_LABELS, tags=("button", "div", "a"))

        await self.page.wait_for_selector(_MODAL, timeout=10000)
        await self.wait(random.uniform(0.6, 1.2))

        if note:
            await self._click_control(_ADD_NOTE_LABELS, tags=("button",))
            textarea = await self.page.wait_for_selector(_INVITE_NOTE_TEXTAREA, timeout=8000)
            await textarea.click()
            await self._human_type(note)
            await self.wait(random.uniform(0.5, 1.0))

        if dry_run:
            shot = str(Path("/tmp") / "oto-linkedin-invitation.png")
            await self.screenshot(shot, full_page=False)
            await self.page.keyboard.press("Escape")
            return {
                "status": "dry_run",
                "action": "invitation",
                "profile": profile_url,
                "note": note,
                "screenshot": shot,
            }

        send_labels = _SEND_LABELS if note else (_SEND_NO_NOTE_LABELS + _SEND_LABELS)
        await self._click_control(send_labels, tags=("button",))
        await self.wait(random.uniform(1.5, 2.5))

        return {"status": "sent", "action": "invitation", "profile": profile_url, "note": note}
