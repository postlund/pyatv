from pyatv.support.url import is_url, is_url_or_scheme


def test_is_url_accepts_http_url():
    assert is_url("http://example.com") is True


def test_is_url_accepts_app_url():
    assert (
        is_url(
            "com.apple.tv://tv.apple.com/show/marvels-spidey-and-his-amazing-friends/umc.cmc.3ambs8tqwzphbn0u8e9g76x7m?profile=kids&action=play"
        )
        is True
    )


def test_is_url_rejects_bundle_id():
    assert is_url("com.apple.tv") is False


def test_is_url_rejects_scheme():
    assert is_url("com.apple.tv://") is False


def test_is_url_or_scheme_accepts_http_url():
    assert is_url_or_scheme("http://example.com") is True


def test_is_url_or_scheme_accepts_app_url():
    assert (
        is_url_or_scheme(
            "com.apple.tv://tv.apple.com/show/marvels-spidey-and-his-amazing-friends/umc.cmc.3ambs8tqwzphbn0u8e9g76x7m?profile=kids&action=play"
        )
        is True
    )


def test_is_url_or_scheme_rejects_bundle_id():
    assert is_url_or_scheme("com.apple.tv") is False


def test_is_url_or_scheme_rejects_scheme():
    assert is_url_or_scheme("com.apple.tv://") is True
