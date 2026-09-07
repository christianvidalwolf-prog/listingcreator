import io
import json
import unittest
import openpyxl
from api._weights import weight_grams
from api._bulk_import import generate_bulk_import_excel
from api.generate import parse_ai_response


class WeightTests(unittest.TestCase):
    def test_units_and_unknowns(self):
        for raw, expected in [('265 gr',265), ('0,265 kg',265), ('12.5 g',12.5),
                              (200,200), (None,None), ('-',None), (0,None),
                              (-2,None), (True,None), ('NaN',None), ('2 lb',None)]:
            with self.subTest(raw=raw): self.assertEqual(weight_grams(raw),expected)

    def test_response_weight(self):
        row=dict(title='Pez',highlights='Adorno',bullet_points=['Uno']*5,description='Decoración',peso_g='0.265 kg')
        self.assertEqual(parse_ai_response(json.dumps(row))['peso_g'],265)
        del row['peso_g']
        self.assertIsNone(parse_ai_response(json.dumps(row))['peso_g'])

    def test_amazon_article_weight_not_package(self):
        data=generate_bulk_import_excel([{'ref':'A','peso_g':'0,265 kg'},{'ref':'B'}])
        w=openpyxl.load_workbook(io.BytesIO(data),keep_vba=True)
        s=w['Plantilla']
        self.assertIn('dataRow=7',s['A1'].value)
        self.assertEqual(s['A7'].value,'ASGI')
        self.assertEqual(s['EC7'].value,265)
        self.assertEqual(s['ED7'].value,'Gramos')
        self.assertIsNone(s['EC8'].value)
        self.assertIsNone(s['ED8'].value)
        self.assertIsNone(s['JQ7'].value)
        self.assertIsNone(s['JR7'].value)

    def test_invalid_export_weight(self):
        with self.assertRaisesRegex(ValueError,'Peso del producto inválido'):
            generate_bulk_import_excel([{'ref':'A','peso_g':-5}])
