"""Test livestream urls."""

from playwright.sync_api import Page, expect

VETINARI_EMAIL = 'vetinari@example.org'
VETINARI_PASSWORD = 've@pwd3289'  # nosec


def wait_until_recaptcha_loaded(page: Page) -> None:
    page.wait_for_selector(
        '#form-passwordlogin > div.g-recaptcha > div > div.grecaptcha-logo > iframe',
        timeout=10000,
    )


def test_login_add_livestream(
    db_session, live_server, user_vetinari, project_expo2010, page: Page
):
    user_vetinari.add_email(VETINARI_EMAIL)
    user_vetinari.password = VETINARI_PASSWORD
    db_session.commit()
    page.goto(live_server.url)
    page.get_by_role("link", name="Login").click()
    wait_until_recaptcha_loaded(page)
    page.wait_for_selector('input[name=username]').fill(VETINARI_EMAIL)
    page.click('#use-password-login')
    page.wait_for_selector('input[name=password]').fill(VETINARI_PASSWORD)
    page.click('#login-btn')
    assert (
        page.wait_for_selector('.alert__text').inner_text() == "You are now logged in"
    )
    page.goto(project_expo2010.absolute_url)
    page.get_by_label("Update livestream URLs").click()
    page.get_by_label("Livestream URLs. One per line").click()
    page.get_by_label("Livestream URLs. One per line").fill(
        "https://www.youtube.com/watch?v=dQw4w9WgXcQ\nhttps://vimeo.com/336892869\nhttps://player.vimeo.com/video/860038461?h=87fb31038b"
    )
    page.get_by_role("button", name="Save changes").click()
    expect(
        page.frame_locator(
            "internal:role=tabpanel[name=\"Livestream\"i] >> iframe"
        ).get_by_label("YouTube Video Player")
    ).to_contain_text("Rick Astley - Never Gonna Give You Up (Official Music Video)")
    page.get_by_role("tab", name="Livestream 2").click()
    expect(
        page.frame_locator(
            "internal:role=tabpanel[name=\"Livestream\"i] >> iframe"
        ).get_by_role("banner")
    ).to_contain_text("Rick Astley - Never Gonna Give You Up (Video)")
    page.get_by_role("tab", name="Livestream 3").click()
    expect(
        page.frame_locator(
            "internal:role=tabpanel[name=\"Livestream\"i] >> iframe"
        ).get_by_role("banner")
    ).to_contain_text(
        "Practical SLSA for developers and application security professionals"
    )
