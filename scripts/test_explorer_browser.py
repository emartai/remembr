"""Real Chromium acceptance against a running local Remembr instance.

Install Playwright in a test environment. Pass --browser-executable to reuse an
installed Chromium. Uses only a newly created synthetic account; deletes its
memory content and revokes its principal credentials in finally. Does not save
credentials, browser storage state, traces or HAR files.
"""

import argparse
import json
import re
import secrets
import time
import uuid
from datetime import UTC, datetime, timedelta, timezone
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from playwright.sync_api import expect, sync_playwright


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", default="http://127.0.0.1:8000")
    parser.add_argument("--browser-executable")
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    root, base = Path(args.output).resolve(), args.url.rstrip("/")
    root.mkdir(parents=True, exist_ok=True)
    result = {
        "result": "incomplete",
        "checks": [],
        "browser": "Chromium",
        "screenshots": [],
    }
    owner, spaces, principals = None, [], []
    browser = None

    def api(method, path, body=None, key=None, expected=200):
        headers = {"Content-Type": "application/json"}
        if key:
            headers["X-API-Key"] = key
        elif owner:
            headers["Authorization"] = "Bearer " + owner
        req = Request(
            base + "/api/v1" + path,
            method=method,
            headers=headers,
            data=json.dumps(body).encode() if body is not None else None,
        )
        try:
            response = urlopen(req, timeout=40)
        except HTTPError as error:
            response = error
        with response:
            assert response.status == expected, (
                method,
                path,
                response.status,
                expected,
            )
            return json.load(response).get("data")

    def passed(name):
        result["checks"].append(name)
        print("PASS " + name, flush=True)

    try:
        marker = uuid.uuid4().hex
        email, password = (
            "explorer-" + marker + "@example.com",
            secrets.token_urlsafe(24),
        )
        owner = api(
            "POST",
            "/auth/register",
            {
                "email": email,
                "password": password,
                "org_name": "Synthetic browser acceptance",
            },
            expected=201,
        )["access_token"]
        with sync_playwright() as p:
            launch = {"headless": True}
            if args.browser_executable:
                launch["executable_path"] = args.browser_executable
            browser = p.chromium.launch(**launch)
            result["browser_version"] = browser.version
            context = browser.new_context(
                viewport={"width": 1440, "height": 1000}, timezone_id="Africa/Lagos"
            )
            page = context.new_page()
            errors, external = [], []
            page.on("pageerror", lambda error: errors.append(str(error)))
            page.on(
                "request",
                lambda request: (
                    external.append(request.url)
                    if not request.url.startswith(base + "/")
                    else None
                ),
            )
            page.goto(base + "/explorer")
            expect(page.locator("#connection")).to_be_visible()
            page.keyboard.press("Tab")
            expect(page.locator("#credential")).to_be_focused()

            def screenshot(name):
                page.screenshot(
                    path=str(root / name),
                    full_page=True,
                    mask=[
                        page.locator("#credential"),
                        page.locator("#password"),
                        page.locator("#new-credential"),
                    ],
                )
                result["screenshots"].append(name)

            screenshot("connection.png")
            passed("connection screen and keyboard focus")
            page.locator("#credential").fill("rmsp_invalid_browser_test")
            page.locator("#connect-form button").click()
            expect(page.locator("#notice")).to_contain_text("401")
            expect(page.locator("#workspace")).to_be_hidden()
            passed("invalid credentials produce an error without exposing workspace")

            def login():
                if not page.locator("#login-form").is_visible():
                    page.get_by_text(
                        "Sign in with your Remembr account", exact=True
                    ).click()
                page.locator("#email").fill(email)
                page.locator("#password").fill(password)
                page.locator("#login-form button").click()
                expect(page.locator("#workspace")).to_be_visible()

            def open_details(id):
                if not page.locator("#" + id).evaluate("element => element.open"):
                    page.locator("#" + id + " > summary").click()

            def post(path, click):
                with page.expect_response(
                    lambda response: (
                        response.url == base + "/api/v1" + path
                        and response.request.method == "POST"
                    )
                ) as pending:
                    click()
                assert pending.value.status == 201
                return pending.value.json()["data"]

            login()
            expect(page.locator("#search-info")).to_contain_text("Create a project")
            expect(page.locator("#password")).to_have_value("")
            passed("account login and empty workspace")
            open_details("management")
            page.locator("#project-name").fill("Browser project")
            project = post(
                "/projects", lambda: page.locator("#new-project button").click()
            )
            expect(page.locator("#project")).to_have_value(project["id"])
            for name in ("Main", "Other"):
                page.locator("#space-name").fill(name)
                space = post(
                    f"/projects/{project['id']}/spaces",
                    lambda: page.locator("#new-space button").click(),
                )
                spaces.append(space["id"])
                expect(page.locator("#space")).to_have_value(space["id"])
            main_space, other_space = spaces
            page.locator("#space").select_option(main_space)
            expect(page.locator("#search-info")).to_contain_text("0 memories")
            passed("project/space creation selects new resources and switching works")

            finding = "uifinding" + marker
            original_content = (
                finding
                + ' Original decision. <img src=x onerror="window.injected=true">'
            )
            open_details("editor")
            page.locator("#content").fill(original_content)
            page.locator("#source").fill("synthetic:browser-design.md")
            original = post(
                f"/projects/spaces/{main_space}/memories",
                lambda: page.locator("#save-form button").click(),
            )
            expect(page.locator("#notice")).to_contain_text("Saved " + original["id"])
            card = page.locator(f'[data-memory-id="{original["id"]}"]')
            expect(card).to_contain_text(original_content)
            assert card.locator("img").count() == 0 and page.evaluate(
                "window.injected === undefined"
            )
            expect(card.locator(".meta")).to_contain_text("synthetic:browser-design.md")
            expect(card.locator(".meta")).to_contain_text("Author user:")
            expect(page.locator("#search-info")).to_contain_text(
                "Scores are not probabilities"
            )
            passed(
                "UI save, source/authorship/ranking visibility and literal content rendering"
            )

            def search(query="", mode="keyword", budget=12000, history=False):
                page.locator("#query").fill(query)
                page.locator("#mode").select_option(mode)
                page.locator("#budget").fill(str(budget))
                page.locator("#history").set_checked(history)
                page.locator("#search-form button").click()
                expect(page.locator("#results")).to_have_attribute("aria-busy", "false")

            deadline = time.monotonic() + 90
            while time.monotonic() < deadline:
                if (
                    api(
                        "GET",
                        f"/projects/spaces/{main_space}/memories/{original['id']}/status",
                    )["embedding_status"]
                    == "ready"
                ):
                    break
                time.sleep(1)
            else:
                raise AssertionError("Real embedding did not become ready")
            for mode in ("keyword", "semantic", "hybrid"):
                search(finding, mode)
                expect(
                    page.locator(f'[data-memory-id="{original["id"]}"]')
                ).to_be_visible()
                expect(page.locator("#search-info")).to_contain_text("· " + mode + " ·")
            passed("keyword, semantic and hybrid search using real local embeddings")

            search(finding)
            card = page.locator(f'[data-memory-id="{original["id"]}"]')
            card.get_by_role("button", name="Correct", exact=True).click()
            expect(page.locator("#content")).to_have_value(original_content)
            page.locator("#content").fill(
                finding + " Corrected decision from the browser."
            )
            page.locator("#expires").fill(
                (
                    datetime.now(timezone(timedelta(hours=1))) + timedelta(days=1)
                ).strftime("%Y-%m-%dT%H:%M")
            )
            correction = post(
                f"/projects/spaces/{main_space}/memories",
                lambda: page.locator("#save-form button").click(),
            )
            expect(page.locator("#notice")).to_contain_text("Saved " + correction["id"])
            assert (
                correction["supersedes_id"] == original["id"]
                and correction["expires_at"]
            )
            for id in ("content", "source", "supersedes", "expires"):
                expect(page.locator("#" + id)).to_have_value("")
            corrected = page.locator(f'[data-memory-id="{correction["id"]}"]')
            corrected.get_by_role("button", name="View previous version").click()
            expect(corrected.locator(".revision")).to_contain_text(original_content)
            expect(corrected.locator(".revision")).to_contain_text(
                original["author_id"]
            )
            passed(
                "correction lineage, previous-version inspection, expiry and cleared save fields"
            )
            screenshot("desktop-correction.png")

            full = api(
                "GET", f"/projects/spaces/{main_space}/memories/{correction['id']}"
            )
            detail_pattern = (
                "**/api/v1/projects/spaces/"
                + main_space
                + "/memories/"
                + correction["id"]
            )
            for state in ("pending", "failed"):
                payload = {
                    **full,
                    "embedding_status": state,
                    "embedding_error": "Synthetic processing failure"
                    if state == "failed"
                    else None,
                }
                page.route(
                    detail_pattern,
                    lambda route, _request, data=payload: route.fulfill(
                        status=200, json={"data": data}
                    ),
                )
                corrected.get_by_role("button", name="Inspect / refresh").click()
                expect(corrected.locator(".badge")).to_contain_text(
                    "embedding " + state
                )
                if state == "failed":
                    expect(corrected.locator(".badge")).to_contain_text(
                        "Synthetic processing failure"
                    )
                page.unroute(detail_pattern)
            corrected.get_by_role("button", name="Inspect / refresh").click()
            expect(corrected.locator(".badge")).to_contain_text("embedding ready")
            passed(
                "pending/failed UI rendering with controlled responses; real ready refresh"
            )

            pagination = "pagination" + marker
            expected_ids = []
            for i in range(3):
                expected_ids.append(
                    api(
                        "POST",
                        f"/projects/spaces/{main_space}/memories",
                        {
                            "content": pagination + " long entry " + str(i),
                            "idempotency_key": "page-" + str(i),
                        },
                        expected=201,
                    )["id"]
                )
            search(pagination, budget=5)
            seen = []
            for i in range(3):
                expect(page.locator(".card")).to_have_count(1)
                id = page.locator(".card").get_attribute("data-memory-id")
                seen.append(id)
                if i < 2:
                    expect(page.locator("#more")).to_be_visible()
                    page.locator("#more").click()
                    expect(page.locator(f'[data-memory-id="{id}"]')).to_have_count(0)
                else:
                    expect(page.locator("#more")).to_be_hidden()
            assert set(seen) == set(expected_ids) and len(set(seen)) == 3
            page.locator("#previous").click()
            expect(page.locator(".card")).to_have_attribute("data-memory-id", seen[1])
            page.locator(".card").get_by_role(
                "button", name="Inspect / refresh"
            ).click()
            expect(page.locator(".card pre").first).to_contain_text(pagination)
            page.locator(".card").get_by_role(
                "button", name="Correct", exact=True
            ).click()
            expect(page.locator("#content")).to_have_value(
                api("GET", f"/projects/spaces/{main_space}/memories/{seen[1]}")[
                    "content"
                ]
            )
            passed(
                "context-budget pagination, previous page, full inspection "
                "and complete correction text"
            )

            page.locator("#space").select_option(other_space)
            expect(page.locator(".card")).to_have_count(0)
            expect(page.locator("#content")).to_have_value("")
            page.locator("#space").select_option(main_space)
            expect(page.locator(".card")).not_to_have_count(0)
            passed("space isolation and draft reset on space change")

            # Delay one real detail request, then switch spaces before it completes.
            late = []
            detail = api("GET", f"/projects/spaces/{main_space}/memories/{seen[1]}")
            detail_route = (
                "**/api/v1/projects/spaces/" + main_space + "/memories/" + seen[1]
            )
            page.route(detail_route, lambda route: late.append(route))
            page.locator(f'[data-memory-id="{seen[1]}"]').get_by_role(
                "button", name="Correct", exact=True
            ).click()
            page.locator("#space").select_option(other_space)
            expect(page.locator("#search-info")).to_contain_text("0 memories")
            assert len(late) == 1
            late[0].fulfill(status=200, json={"data": detail})
            page.unroute(detail_route)
            page.wait_for_timeout(200)
            expect(page.locator("#content")).to_have_value("")
            page.locator("#space").select_option(main_space)
            expect(page.locator(".card")).not_to_have_count(0)
            passed("late correction response cannot populate a different space")

            expiring = api(
                "POST",
                f"/projects/spaces/{main_space}/memories",
                {
                    "content": "expiring " + marker,
                    "idempotency_key": "expiry",
                    "expires_at": (
                        datetime.now(UTC) + timedelta(seconds=3)
                    ).isoformat(),
                },
                expected=201,
            )
            time.sleep(4)
            search()
            expect(page.locator(f'[data-memory-id="{expiring["id"]}"]')).to_have_count(
                0
            )
            search(history=True)
            expect(
                page.locator(f'[data-memory-id="{expiring["id"]}"] .badge')
            ).to_contain_text("expired")
            expect(
                page.locator(f'[data-memory-id="{original["id"]}"] .badge')
            ).to_contain_text("superseded")
            page.locator("#query").fill("incompatible history query")
            page.locator("#search-form button").click()
            expect(page.locator("#notice")).to_contain_text("Clear the search query")
            passed(
                "real expiry exclusion, history browsing and history/query validation"
            )

            search(finding)
            corrected = page.locator(f'[data-memory-id="{correction["id"]}"]')
            page.once("dialog", lambda dialog: dialog.dismiss())
            corrected.get_by_role("button", name="Delete", exact=True).click()
            expect(corrected).to_be_visible()
            page.once("dialog", lambda dialog: dialog.accept())
            corrected.get_by_role("button", name="Delete", exact=True).click()
            expect(corrected).to_have_count(0)
            api(
                "GET",
                f"/projects/spaces/{main_space}/memories/{correction['id']}",
                expected=404,
            )
            passed(
                "delete cancellation, confirmation and removal from API/visible results"
            )

            open_details("management")
            page.locator("#agent-name").fill("Browser test connection")
            principal = post(
                "/projects/principals",
                lambda: page.locator("#new-agent button").click(),
            )
            principals.append(principal["id"])
            expect(page.locator("#new-credential")).to_contain_text(principal["id"])
            page.locator("#grant-read").check()
            page.locator("#grant button").first.click()
            expect(page.locator("#notice")).to_contain_text("Permissions saved")
            other_context = browser.new_context(viewport={"width": 1280, "height": 900})
            reader = other_context.new_page()
            reader.on("pageerror", lambda error: errors.append(str(error)))
            reader.goto(base + "/explorer")
            reader.locator("#credential").fill(principal["api_key"])
            reader.locator("#connect-form button").click()
            expect(reader.locator("#workspace")).to_be_visible()
            expect(reader.locator("#editor")).to_be_hidden()
            expect(reader.locator("#management")).to_be_hidden()
            expect(
                reader.get_by_role("button", name="Delete", exact=True)
            ).to_have_count(0)
            expect(
                reader.get_by_role("button", name="Correct", exact=True)
            ).to_have_count(0)
            api(
                "POST",
                f"/projects/spaces/{main_space}/memories",
                {"content": "must not be saved", "idempotency_key": "denied"},
                key=principal["api_key"],
                expected=404,
            )
            passed(
                "UI credential issuance/grants and read-only UI plus server enforcement"
            )

            page.locator("#grant-read").uncheck()
            page.locator("#grant-write").check()
            page.locator("#grant button").first.click()
            expect(page.locator("#notice")).to_contain_text("Permissions saved")
            reader.locator("#refresh").click()
            expect(reader.locator("#editor")).to_be_visible()
            expect(reader.locator("#search-form")).to_be_hidden()
            expect(reader.locator(".card")).to_have_count(0)
            reader.locator("#editor summary").click()
            reader.locator("#content").fill("Write-only synthetic finding")
            with reader.expect_response(
                lambda r: (
                    r.url.endswith(f"/spaces/{main_space}/memories")
                    and r.request.method == "POST"
                )
            ) as pending:
                reader.locator("#save-form button").click()
            written = pending.value.json()["data"]
            expect(reader.locator("#notice")).to_contain_text("Saved " + written["id"])
            assert (
                api("GET", f"/projects/spaces/{main_space}/memories/{written['id']}")[
                    "author_id"
                ]
                == principal["id"]
            )
            api(
                "GET",
                f"/projects/spaces/{main_space}/memories/{written['id']}",
                key=principal["api_key"],
                expected=404,
            )
            passed("updated grants, write-only save and no read access")

            page.locator("#grant-write").uncheck()
            page.locator("#grant button").first.click()
            expect(page.locator("#notice")).to_contain_text("Permissions saved")
            reader.locator("#refresh").click()
            expect(reader.locator("#search-info")).to_contain_text(
                "No accessible memory spaces"
            )
            expect(reader.locator("#editor")).to_be_hidden()
            page.once("dialog", lambda dialog: dialog.accept())
            page.locator("#revoke").click()
            expect(page.locator("#notice")).to_contain_text("Credential revoked")
            reader.locator("#refresh").click()
            expect(reader.locator("#connection")).to_be_visible()
            expect(reader.locator("#notice")).to_contain_text("revoked")
            expect(reader.locator(".card")).to_have_count(0)
            other_context.close()
            passed("removed grants and revoked credentials clear inaccessible UI")

            page.locator("#management > summary").click()
            search(pagination)
            pattern = "**/api/v1/projects/spaces/*/search"
            page.route(
                pattern,
                lambda route: route.fulfill(
                    status=503,
                    json={"error": {"message": "Synthetic service unavailable"}},
                ),
            )
            page.locator("#search-form button").click()
            expect(page.locator("#notice")).to_contain_text(
                "503: Synthetic service unavailable"
            )
            expect(page.locator(".card")).to_have_count(0)
            page.unroute(pattern)
            page.locator("#search-form button").click()
            expect(page.locator(".card")).to_have_count(3)
            passed("controlled service error, stale-result clearing and retry recovery")

            for width in (390, 320):
                page.set_viewport_size({"width": width, "height": 844})
                assert page.evaluate(
                    "document.documentElement.scrollWidth <= innerWidth"
                ), f"Horizontal overflow at {width}px"
                expect(page.locator("#query")).to_be_visible()
            page.set_viewport_size({"width": 390, "height": 844})
            screenshot("mobile.png")
            page.set_viewport_size({"width": 1440, "height": 1000})
            passed("390px and 320px layouts without horizontal overflow")

            held = []
            page.route(pattern, lambda route: held.append(route))
            page.locator("#search-form button").click()
            expect(page.locator("#results")).to_have_attribute("aria-busy", "true")
            open_details("editor")
            page.locator("#content").fill("Private synthetic draft")
            page.locator("#disconnect").click()
            expect(page.locator("#connection")).to_be_visible()
            expect(page.locator("#content")).to_have_value("")
            for route in held:
                try:
                    route.continue_()
                except Exception:
                    pass  # The fetch may already have been cancelled by disconnect.
            page.unroute(pattern)
            expect(page.locator("#workspace")).to_be_hidden()
            expect(page.locator(".card")).to_have_count(0)
            assert page.evaluate(
                "localStorage.length === 0 && sessionStorage.length === 0"
            )
            login()
            expect(page.locator("#content")).to_have_value("")
            page.reload()
            expect(page.locator("#connection")).to_be_visible()
            expect(page.locator("#credential")).to_have_value("")
            passed(
                "loading state, disconnect cancellation, cleared drafts "
                "and no persisted credentials"
            )
            assert errors == [], errors
            assert external == [], external
            result["page_errors"] = errors
            result["external_page_requests"] = external
            result["result"] = "passed"
            browser.close()
            browser = None
    except Exception as error:
        result["error"] = re.sub(
            r"rmsp_[A-Za-z0-9_-]+", "[redacted credential]", str(error)
        )[:1500]
        raise
    finally:
        if browser:
            try:
                browser.close()
            except Exception:
                pass
        try:
            for space in spaces:
                rows = api(
                    "POST",
                    f"/projects/spaces/{space}/search",
                    {"include_inactive": True, "limit": 100},
                )["results"]
                for row in rows:
                    api("DELETE", f"/projects/spaces/{space}/memories/{row['id']}")
            for principal in principals:
                api("DELETE", "/projects/principals/" + principal)
            result["synthetic_content_cleaned_and_credentials_revoked"] = True
        finally:
            (root / "browser-results.json").write_text(
                json.dumps(result, indent=2) + "\n", encoding="utf-8"
            )
    print(json.dumps(result, indent=2), flush=True)


if __name__ == "__main__":
    main()
