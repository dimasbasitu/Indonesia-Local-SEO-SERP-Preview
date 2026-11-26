import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

import requests
from streamlit.testing.v1 import AppTest

import scraper
from renderer import build_serp_viewer, safe_url


def response(payload, status=200, reason="OK"):
    mock = MagicMock()
    mock.ok = 200 <= status < 400
    mock.status_code = status
    mock.reason = reason
    mock.json.return_value = payload
    return mock


class SerperClientTest(unittest.TestCase):
    def test_search_posts_serper_payload_and_returns_raw_response(self):
        payload = {
            "searchParameters": {"q": "jasa seo", "location": "Yogyakarta,Indonesia"},
            "organic": [{"position": 1, "title": "Result", "link": "https://example.com"}],
        }
        with patch.object(scraper.requests, "post", return_value=response(payload)) as post:
            result = scraper.run_serp_check("jasa seo", "Yogyakarta,Indonesia", api_key="secret")

        self.assertIs(result, payload)
        post.assert_called_once()
        self.assertEqual(post.call_args.args[0], "https://google.serper.dev/search")
        request_payload = post.call_args.kwargs["json"]
        self.assertEqual(request_payload["q"], "jasa seo")
        self.assertEqual(request_payload["location"], "Yogyakarta,Indonesia")
        self.assertEqual(request_payload["gl"], "id")
        self.assertEqual(request_payload["hl"], "id")
        self.assertEqual(request_payload["num"], 10)
        self.assertFalse(request_payload["autocorrect"])
        self.assertEqual(post.call_args.kwargs["headers"]["X-API-KEY"], "secret")
        self.assertNotIn("secret", str(request_payload))

    def test_missing_api_key_is_rejected_before_request(self):
        with patch.dict("os.environ", {}, clear=True), patch.object(scraper.requests, "post") as post:
            with self.assertRaisesRegex(scraper.SerperError, "belum dikonfigurasi"):
                scraper.run_serp_check("test", "Indonesia")
        post.assert_not_called()

    def test_api_error_is_reported_without_key(self):
        failed = response({"message": "Not enough credits"}, status=403, reason="Forbidden")
        with patch.object(scraper.requests, "post", return_value=failed):
            with self.assertRaises(scraper.SerperError) as caught:
                scraper.run_serp_check("test", "Indonesia", api_key="do-not-leak")
        self.assertIn("Not enough credits", str(caught.exception))
        self.assertNotIn("do-not-leak", str(caught.exception))

    def test_network_error_does_not_echo_key(self):
        error = requests.ConnectionError("failed with key=secret")
        with patch.object(scraper.requests, "post", side_effect=error):
            with self.assertRaises(scraper.SerperError) as caught:
                scraper.run_serp_check("test", "Indonesia", api_key="secret")
        self.assertNotIn("secret", str(caught.exception))


class RendererTest(unittest.TestCase):
    def test_serper_preview_and_json_are_mapped(self):
        payload = {
            "searchParameters": {"q": "<script>alert(1)</script>", "location": "Yogyakarta"},
            "organic": [{
                "position": 1,
                "title": "Safe result",
                "link": "https://example.com/page",
                "snippet": "<b>not html</b>",
                "sitelinks": [{"title": "About", "link": "https://example.com/about"}],
            }],
        }
        rendered = build_serp_viewer(payload)
        self.assertIn("Preview SERP", rendered)
        self.assertIn("Raw JSON", rendered)
        self.assertIn("organic-0", rendered)
        self.assertIn("serp-result-selected", rendered)
        self.assertIn('role=\"button\"', rendered)
        self.assertIn('tabindex=\"0\"', rendered)
        self.assertNotIn("<script>alert(1)</script>", rendered)
        self.assertIn("&lt;b&gt;not html&lt;/b&gt;", rendered)

    def test_unsafe_url_is_rejected(self):
        self.assertEqual(safe_url("javascript:alert(1)"), "")

    def test_place_is_mapped_to_its_json_object(self):
        payload = {"places": [{"title": "Local business", "website": "https://local.example/"}]}
        rendered = build_serp_viewer(payload)
        self.assertIn("place-0", rendered)
        self.assertIn('id=\"json-place-0\"', rendered)
        self.assertIn("https://local.example/", rendered)

    def test_shopping_result_is_mapped_to_preview_and_json(self):
        payload = {"shopping": [{"title": "Produk", "link": "https://shop.example/product"}]}
        rendered = build_serp_viewer(payload)
        self.assertIn("Hasil belanja", rendered)
        self.assertIn("shopping-0", rendered)
        self.assertIn('id=\"json-shopping-0\"', rendered)

    def test_unicode_entity_does_not_break_preview_injection(self):
        payload = {"organic": [{"title": "Café terbaik…", "link": "https://example.com/cafe"}]}
        rendered = build_serp_viewer(payload)
        self.assertIn("organic-0", rendered)
        self.assertIn("Café terbaik", rendered)

    def test_ai_overview_and_ads_are_excluded(self):
        payload = {
            "aiOverview": {"text": "AI_UNIQUE_CONTENT"},
            "ads": [{"title": "SPONSOR_UNIQUE_CONTENT", "link": "https://ads.example/"}],
            "shoppingAds": [{"title": "SHOPPING_AD_UNIQUE", "link": "https://shop.example/"}],
            "organic": [{"title": "ORGANIC_UNIQUE_CONTENT", "link": "https://example.com/"}],
        }
        rendered = build_serp_viewer(payload)
        self.assertNotIn("AI_UNIQUE_CONTENT", rendered)
        self.assertNotIn("SPONSOR_UNIQUE_CONTENT", rendered)
        self.assertNotIn("SHOPPING_AD_UNIQUE", rendered)
        self.assertIn("ORGANIC_UNIQUE_CONTENT", rendered)
        self.assertIn("AI Overview dan sponsor dikecualikan", rendered)

    def test_viewer_has_no_purple_frame(self):
        rendered = build_serp_viewer({})
        self.assertNotIn("#4d68ee", rendered.lower())
        self.assertIn("border: 1px solid #3f4147", rendered)


class AppTestCase(unittest.TestCase):
    def test_app_loads_without_exception(self):
        app = AppTest.from_file(str(Path(__file__).resolve().parents[1] / "app.py")).run()
        self.assertFalse(app.exception)
        self.assertEqual(app.button[0].label, "Cek SERP")
        self.assertEqual(len(app.tabs), 0)

    def test_failed_search_clears_old_results(self):
        with patch.dict("os.environ", {"SERPER_API_KEY": "test-key"}):
            app = AppTest.from_file(str(Path(__file__).resolve().parents[1] / "app.py")).run()
            app.session_state["serp_result"] = {"organic": []}
            with patch("scraper.run_serp_check", side_effect=scraper.SerperError("API gagal")):
                app.text_input[0].set_value("new search")
                app.button[0].click().run()
        self.assertFalse(app.exception)
        self.assertTrue(app.error)
        self.assertNotIn("serp_result", app.session_state)


if __name__ == "__main__":
    unittest.main()
