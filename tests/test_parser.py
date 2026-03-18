import json
import unittest

from aucorsa.parser import parse_estimations_response


class ParseEstimationsResponseTests(unittest.TestCase):
    def test_parse_multiple_lines_from_html_response(self):
        html = """
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
        response_text = json.dumps(html)

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


if __name__ == "__main__":
    unittest.main()
