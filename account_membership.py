"""Owner-only membership preview and private club application workflow."""
from datetime import datetime, timedelta, timezone
from html import escape
import secrets

from fastapi import Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from auth.auth_storage import update_user, load_users, get_user_by_email
from brand import render_brand_logo, render_site_theme, render_site_footer


def membership_state(user):
    result = dict(user)
    if result.get("membership_test_enabled"):
        try:
            expiry = datetime.fromisoformat(result.get("test_expires_at", ""))
            remaining = max(0, int((expiry - datetime.now(timezone.utc)).total_seconds() + 86399) // 86400)
        except (ValueError, TypeError):
            remaining = 0
        result["days_left"] = remaining
        result["is_active"] = remaining > 0 and result.get("plan") in ("player", "host")
        result["auto_renew"] = False
    return result


def account_context(request, user):
    result = membership_state(user)
    result["_can_test"] = bool(user.get("membership_test_enabled"))
    result["_can_enable_test"] = request.cookies.get("admin_auth") == "yes"
    result["_csrf"] = request.session.setdefault("account_csrf", secrets.token_urlsafe(32))
    return result


ACCOUNT_CSS = """<style>
.tr-info-card{border:1px solid rgba(200,223,221,.12);border-radius:22px;padding:28px;margin:24px 0;background:linear-gradient(145deg,#202d32e8,#172126e8)}
.tr-info-card h2{font-size:22px;margin:0 0 14px}.tr-info-card p{color:#a5b4b6;line-height:1.6}.tr-info-card form{max-width:620px;margin-top:26px}.tr-info-card label{display:block;font-size:13px;color:#dbe6e4}.tr-info-card input,.tr-info-card select,.tr-info-card textarea{display:block;width:100%;box-sizing:border-box;padding:12px 14px;margin-top:8px;border-radius:11px;border:1px solid #a8d8c430;background:#101b21;color:#edf3f2;font:inherit;min-height:46px}.tr-info-card textarea{min-height:110px;resize:vertical}.tr-info-card input:focus-visible,.tr-info-card select:focus-visible,.tr-info-card textarea:focus-visible{outline:2px solid #a8d8c4;outline-offset:2px}@media(max-width:600px){.tr-info-card{padding:22px}}
</style>"""


def page(title, body, user):
    from auth.profile_view import render_account_menu
    return f'''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>{escape(title)} · TableRadar</title>{render_site_theme()}{ACCOUNT_CSS}</head><body style="margin:0"><header class="tr-site-header">{render_brand_logo('/')}{render_account_menu(user)}</header><main class="tr-site-main"><h1 class="tr-page-title">{escape(title)}</h1>{body}<p><a class="tr-button" href="/profile">← My account</a></p></main>{render_site_footer()}</body></html>'''


def install_account_routes(app, get_current_user):
    def permitted(request, csrf, allow_bootstrap=False):
        user = get_current_user(request)
        token = request.session.get("account_csrf", "")
        if not user or not token or not secrets.compare_digest(token, csrf):
            return None
        if not user.get("membership_test_enabled") and not (allow_bootstrap and request.cookies.get("admin_auth") == "yes"):
            return None
        return user

    @app.post("/account/test-membership")
    def test_membership(request: Request, plan: str = Form(""), csrf: str = Form("")):
        user = permitted(request, csrf, allow_bootstrap=plan == "reset")
        if not user or plan not in ("reset", "player", "host"):
            return HTMLResponse("Membership preview is not available for this account.", status_code=403)
        # One explicit reset enables this private test workflow for the signed-in account only.
        now = datetime.now(timezone.utc)
        previous = {key: user.get(key) for key in ("plan", "role", "is_active", "days_left", "auto_renew", "plan_started_at", "plan_expires_at")}
        fields = dict(membership_test_enabled=True, plan="inactive" if plan == "reset" else plan,
                      role="member" if plan == "reset" else plan, is_active=plan != "reset",
                      days_left=0 if plan == "reset" else 30, auto_renew=False,
                      test_expires_at="" if plan == "reset" else (now + timedelta(days=30)).isoformat(),
                      plan_started_at="" if plan == "reset" else now.strftime("%d/%m/%Y"),
                      plan_expires_at="" if plan == "reset" else (now + timedelta(days=30)).strftime("%d/%m/%Y"))
        if not user.get("membership_test_enabled"):
            fields["membership_before_test"] = previous
        update_user(user["email"], **fields)
        request.session["plan"] = fields["plan"]
        request.session["is_active"] = "1" if fields["is_active"] else "0"
        return RedirectResponse("/profile", status_code=303)

    @app.get("/host", response_class=HTMLResponse)
    def host_account(request: Request):
        user = get_current_user(request)
        if not user:
            return RedirectResponse("/signin_login", status_code=303)
        user = account_context(request, user)
        if not user.get("is_active") or user.get("plan") != "host":
            return RedirectResponse("/profile", status_code=303)
        club = user.get("club_application") or {}
        safe = lambda value: escape(str(value or ""), quote=True)
        csrf = safe(user["_csrf"])
        status_labels = {"pending": "Awaiting operator review", "approved": "Approved — operator manages table updates", "needs_changes": "Changes requested by the operator"}
        club_status = status_labels.get(club.get("status"), "Awaiting operator review") if club else "No club submitted"
        review_note = f'<p>Operator note: {safe(club.get("review_note"))}</p>' if club.get("review_note") else ""
        body = f'''<p class="tr-page-intro">Your club, listing request and membership in one place.</p><section class="tr-info-card"><h2>Membership</h2><p>{'Free test membership — no payment or automatic renewal.' if user.get('membership_test_enabled') else 'Host membership'}</p><p>{int(user.get('days_left') or 0)} days remaining · Valid until {safe(user.get('plan_expires_at') or 'Not recorded')}</p></section><section class="tr-info-card"><h2>Your club</h2><p>Status: <strong>{club_status}</strong></p>{review_note}<p>One club per Host account. Submitting details does not publish tables or join a poker club. The operator reviews the request and updates table information manually.</p><form method="post" action="/host/club"><input type="hidden" name="csrf" value="{csrf}"><p><label>Club name<br><input name="club_name" required maxlength="120" value="{safe(club.get('club_name'))}"></label></p><p><label>Application<br><select name="application">{''.join(f'<option{chr(32)+"selected" if club.get("application")==name else ""}>{name}</option>' for name in ('ClubGG','X Poker','PPPoker','Other'))}</select></label></p><p><label>Club ID or code<br><input name="club_code" required maxlength="80" value="{safe(club.get('club_code'))}"></label></p><p><label>Notes for the operator<br><textarea name="notes" maxlength="1000">{safe(club.get('notes'))}</textarea></label></p><button class="tr-button" type="submit">{'Update club request' if club else 'Submit club for review'}</button></form></section>'''
        return page("Host dashboard", body, user)

    @app.post("/host/club")
    def submit_club(request: Request, csrf: str = Form(""), club_name: str = Form(""), application: str = Form(""), club_code: str = Form(""), notes: str = Form("")):
        user = get_current_user(request)
        token = request.session.get("account_csrf", "")
        if not user or not token or not secrets.compare_digest(token, csrf) or not user.get("is_active") or user.get("plan") != "host":
            return HTMLResponse("Host access required.", status_code=403)
        if not club_name.strip() or not club_code.strip() or len(club_name) > 120 or len(club_code) > 80 or len(notes) > 1000 or application not in ("ClubGG", "X Poker", "PPPoker", "Other"):
            return HTMLResponse("Check the club name, application and code.", status_code=400)
        update_user(user["email"], club_application=dict(club_name=club_name.strip(), application=application, club_code=club_code.strip(), notes=notes.strip(), status="pending", submitted_at=datetime.now(timezone.utc).isoformat()))
        return RedirectResponse("/host", status_code=303)

    @app.get("/admin/club-requests", response_class=HTMLResponse)
    def club_requests(request: Request):
        if request.cookies.get("admin_auth") != "yes":
            return RedirectResponse("/login", status_code=303)
        safe = lambda value: escape(str(value or ""), quote=True)
        csrf = safe(request.session.setdefault("account_csrf", secrets.token_urlsafe(32)))
        cards = []
        for user in load_users():
            club = user.get("club_application")
            if club:
                state = membership_state(user)
                review_options = ''.join(f'<option value="{value}"{" selected" if club.get("status", "pending") == value else ""}>{label}</option>' for value, label in (("pending", "Pending review"), ("approved", "Approve listing request"), ("needs_changes", "Request changes")))
                cards.append(f'<section class="tr-info-card"><h2>{safe(club.get("club_name"))}</h2><p>{safe(user.get("email"))} · {safe(club.get("application"))} · Club code: {safe(club.get("club_code"))}</p><p>{safe(club.get("status", "pending"))} · Host access: {"active" if state.get("is_active") and state.get("plan")=="host" else "inactive"}</p><p>{safe(club.get("notes"))}</p><form method="post" action="/admin/club-requests/review"><input type="hidden" name="csrf" value="{csrf}"><input type="hidden" name="email" value="{safe(user.get("email"))}"><input type="hidden" name="submitted_at" value="{safe(club.get("submitted_at"))}"><p><label>Review status<select name="status">{review_options}</select></label></p><p><label>Note to the owner<textarea name="review_note" maxlength="1000">{safe(club.get("review_note"))}</textarea></label></p><button class="tr-button" type="submit">Save review</button></form></section>')
        return page("Club requests", ''.join(cards) or '<p>No club requests yet.</p>', get_current_user(request) or {})

    @app.post("/admin/club-requests/review")
    def review_club(request: Request, csrf: str = Form(""), email: str = Form(""), submitted_at: str = Form(""), status: str = Form(""), review_note: str = Form("")):
        token = request.session.get("account_csrf", "")
        if request.cookies.get("admin_auth") != "yes" or not token or not secrets.compare_digest(token, csrf):
            return HTMLResponse("Operator access required.", status_code=403)
        if status not in ("pending", "approved", "needs_changes") or len(review_note) > 1000:
            return HTMLResponse("Invalid review.", status_code=400)
        user = get_user_by_email(email)
        club = (user or {}).get("club_application")
        if not club or club.get("submitted_at", "") != submitted_at:
            return HTMLResponse("The request changed. Reload the review page.", status_code=409)
        update_user(email, club_application=dict(club, status=status, review_note=review_note.strip(), reviewed_at=datetime.now(timezone.utc).isoformat()))
        return RedirectResponse("/admin/club-requests", status_code=303)
