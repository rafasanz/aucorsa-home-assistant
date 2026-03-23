import json
import unittest
from unittest.mock import Mock

import requests
from aucorsa.client import AucorsaClient
from aucorsa.models import PageContext
from aucorsa.parser import parse_estimations_response


HTML_RESPONSE = """
<div class="ppp-content">
  <div class="ppp-stop-label">Parada 101: Escultor Ramón Barba 1ª D.C.</div>
  <div class="ppp-container">
    <div class="ppp-line-number" style="background-color: #65b147">12</div>
    <div class="ppp-line-route">NARANJO - TENDILLAS - SECTOR SUR</div>
    <div class="ppp-estimation">Próximo autobús: <strong>7 minutos</strong></div>
    <div class="ppp-estimation">Siguiente autobús: <strong>21 minutos</strong></div>
  </div>
  <div class="ppp-container">
    <div class="ppp-line-number" style="background-color: #f59a00">46</div>
    <div class="ppp-line-route">COLÓN NORTE - HUERTA DEL HIERRO</div>
    <div class="ppp-estimation">Próximo autobús: <strong>12 minutos</strong></div>
  </div>
</div>
"""


class ParseEstimationsResponseTests(unittest.TestCase):
    def test_parse_multiple_lines_from_html_response(self):
        response_text = json.dumps(HTML_RESPONSE)

        result = parse_estimations_response(
            response_text=response_text,
            stop_id="101",
            line_id_by_visible={"12": "763", "46": "3802"},
        )

        self.assertEqual(result.stop_id, "101")
        self.assertEqual(result.stop_label, "Parada 101: Escultor Ramón Barba 1ª D.C.")
        self.assertEqual(len(result.lines), 2)

        self.assertEqual(result.lines[0].line, "12")
        self.assertEqual(result.lines[0].internal_line_id, "763")
        self.assertEqual(result.lines[0].route, "NARANJO - TENDILLAS - SECTOR SUR")
        self.assertEqual(result.lines[0].line_color, "#65b147")
        self.assertEqual(result.lines[0].next_bus_min, 7)
        self.assertEqual(result.lines[0].following_bus_min, 21)

        self.assertEqual(result.lines[1].line, "46")
        self.assertEqual(result.lines[1].internal_line_id, "3802")
        self.assertEqual(result.lines[1].route, "COLÓN NORTE - HUERTA DEL HIERRO")
        self.assertEqual(result.lines[1].line_color, "#f59a00")
        self.assertEqual(result.lines[1].next_bus_min, 12)
        self.assertIsNone(result.lines[1].following_bus_min)

    def test_parse_accepts_raw_html_and_nested_json_payloads(self):
        response_variants = [
            HTML_RESPONSE,
            json.dumps({"html": HTML_RESPONSE}),
            json.dumps({"data": {"content": HTML_RESPONSE}}),
        ]

        for response_text in response_variants:
            with self.subTest(response=response_text[:20]):
                result = parse_estimations_response(
                    response_text=response_text,
                    stop_id="101",
                    line_id_by_visible={"12": "763", "46": "3802"},
                )
                self.assertEqual(result.stop_label, "Parada 101: Escultor Ramón Barba 1ª D.C.")
                self.assertEqual([line.line for line in result.lines], ["12", "46"])
                self.assertEqual(result.lines[0].next_bus_min, 7)
                self.assertEqual(result.lines[0].following_bus_min, 21)
                self.assertEqual(result.lines[1].next_bus_min, 12)


class ClientContextExtractionTests(unittest.TestCase):
    def test_extracts_nonce_post_id_and_dynamic_api_url(self):
        page_html = """
        <script>
        var ajax_vars = {
          "ajax_nonce":"abc123-_",
          "post_id":"6935",
          "api_url":"https:\\/\\/cdn.aucorsa.es\\/wp-json\\/aucorsa\\/v1"
        };
        </script>
        """

        client = AucorsaClient()

        self.assertEqual(client.extract_nonce(page_html), "abc123-_")
        self.assertEqual(client.extract_post_id(page_html), "6935")
        self.assertEqual(
            client.extract_api_url(page_html),
            "https://cdn.aucorsa.es/wp-json/aucorsa/v1",
        )


class ClientNonceRecoveryTests(unittest.TestCase):
    def test_api_get_refreshes_context_after_invalid_nonce_403(self):
        client = AucorsaClient()
        client._context = PageContext(
            nonce="stale-nonce",
            post_id="6935",
            api_url="https://aucorsa.es/wp-json/aucorsa/v1",
        )

        fresh_context = PageContext(
            nonce="fresh-nonce",
            post_id="6935",
            api_url="https://aucorsa.es/wp-json/aucorsa/v1",
        )

        def _refresh_context():
            client._context = fresh_context
            return fresh_context

        client.refresh_context = Mock(side_effect=_refresh_context)

        invalid_nonce_response = Mock(status_code=403)
        invalid_nonce_response.text = (
            '{"code":"rest_cookie_invalid_nonce","message":"Ha fallado la comprobacion"}'
        )
        invalid_nonce_response.raise_for_status.side_effect = requests.HTTPError("403 invalid nonce")

        success_response = Mock(status_code=200)
        success_response.text = "[]"
        success_response.raise_for_status.return_value = None
        success_response.json.return_value = []

        captured_params: list[dict[str, str]] = []

        def _session_get(*args, **kwargs):
            captured_params.append(dict(kwargs["params"]))
            if len(captured_params) == 1:
                return invalid_nonce_response
            return success_response

        client.session.get = Mock(side_effect=_session_get)

        response = client._api_get("/autocompletion/line", {"term": "12"})

        self.assertIs(response, success_response)
        client.refresh_context.assert_called_once()
        self.assertEqual(client.session.get.call_count, 2)
        self.assertEqual(captured_params[0]["_wpnonce"], "stale-nonce")
        self.assertEqual(captured_params[1]["_wpnonce"], "fresh-nonce")


if __name__ == "__main__":
    unittest.main()
