import json
import threading
import unittest
import urllib.request
import urllib.error
from unittest.mock import patch, MagicMock
from http.server import ThreadingHTTPServer
from api import generate
from server import Handler

class ParsingTests(unittest.TestCase):
    def test_prompt_example_is_valid_json(self):
        for divisor in (1, 3):
            prompt = generate.build_prompt('Adorno', '30x20 cm', divisor)
            example = json.loads(prompt.rsplit('\n', 1)[1])
            self.assertEqual(example['visual_analysis']['status'], 'identified')
            self.assertEqual(len(example['bullet_points']), 5)

    def test_generation_retries_format_failures_once(self):
        args = dict(api_key='key', image_url='https://example.com/a',
                    name='Adorno', dims='30x20 cm', divisor=2)
        row = dict(title='Adorno x2 30x20 cm', highlights='Forma de pez',
                   bullet_points=['Detalle']*5, description='Adorno',
                   visual_analysis={'status':'identified', 'object':'Adorno',
                                    'visible_features':['Forma de pez']})
        valid = json.dumps(row)
        provider = MagicMock(return_value=valid)
        self.assertEqual(generate.generate_listing(provider, args)["title"], row["title"])
        provider.assert_called_once_with(**args)
        for invalid in ('', 'No es JSON', valid[:-10], json.dumps(dict(row, bullet_points=[]))):
            with self.subTest(invalid=invalid):
                provider = MagicMock(side_effect=[invalid, valid])
                self.assertEqual(generate.generate_listing(provider, args)['title'], row['title'])
                self.assertEqual(provider.call_count, 2)
                retry = provider.call_args.kwargs
                for key, value in args.items():
                    self.assertEqual(retry[key], value)
                self.assertIn('PACK DE 2 UNIDADES', retry['prompt_override'])
        provider = MagicMock(return_value='JSON roto')
        with self.assertRaises(generate.ListingFormatError):
            generate.generate_listing(provider, args)
        self.assertEqual(provider.call_count, 2)

    def test_generation_does_not_retry_visual_abstention_or_timeout(self):
        args = dict(api_key='key', image_url='https://example.com/a', name='', dims='', divisor=1)
        for status in ('uncertain', 'unavailable', 'conflict'):
            provider = MagicMock(return_value=json.dumps({'visual_analysis': {'status': status}}))
            with self.subTest(status=status), self.assertRaises(ValueError):
                generate.generate_listing(provider, args)
            provider.assert_called_once()
        provider = MagicMock(side_effect=TimeoutError('timeout'))
        with self.assertRaises(TimeoutError):
            generate.generate_listing(provider, args)
        provider.assert_called_once()

    def test_dimensions(self):
        for raw, expected in [('100x200 cm','100x200 cm'),('100x200 mm','10x20 cm'),('1 m x 20 cm x 50 mm','100x20x5 cm'),('1,25 × 0,5 m','125x50 cm'),('2.55x1.25 cm','2.55x1.25 cm'),('100x200','-'),('0x2 cm','-'),('-2x3 cm','-')]:
            with self.subTest(raw=raw): self.assertEqual(generate.normalize_dimensions(raw), expected)

    def test_json_and_limits(self):
        data=dict(title='Producto '*20,highlights='Detalle '*30,material=None,medidas='100x200 mm',bullet_points=['Bullet']*5,description='Descripción')
        parsed=generate.parse_ai_response('```json\n'+json.dumps(data)+'\n``` extra {}')
        self.assertLessEqual(len(parsed['title']),75)
        self.assertLessEqual(len(parsed['highlights']),125)
        self.assertEqual(parsed['medidas'],'10x20 cm')
        self.assertEqual(parsed['material'],'-')

    def test_backend_keywords_parsing_and_limit(self):
        long_keywords = "florero moderno decoracion hogar jarron ceramica diseno nordico regalo salon mesa centro entrada estanteria terraza boda estilo minimalista artesanal habitacion oficina sala detalles adornos " * 3
        data = dict(
            title='Jarrón blanco',
            highlights='Cerámica mate',
            material='Cerámica',
            medidas='20x10 cm',
            bullet_points=['Bullet 1', 'Bullet 2', 'Bullet 3', 'Bullet 4', 'Bullet 5'],
            description='Descripción completa del jarrón.',
            backend_keywords="florero, decoracion; salon, mesa - regalo: moderno. " + long_keywords
        )
        parsed = generate.parse_ai_response(json.dumps(data))
        self.assertIn('backend_keywords', parsed)
        self.assertLessEqual(len(parsed['backend_keywords']), 250)
        self.assertNotIn(',', parsed['backend_keywords'])
        self.assertNotIn(';', parsed['backend_keywords'])
        self.assertNotIn(':', parsed['backend_keywords'])
        self.assertNotIn('-', parsed['backend_keywords'])

    def test_color_parsing(self):
        cases = [
            ('blanco', 'Blanco'),
            ('MULTICOLOR', 'Multicolor'),
            ('varios colores', 'Multicolor'),
            ('estampado floral multicolor', 'Multicolor'),
            ('azul marino', 'Azul marino'),
            ('', '-'),
            ('-', '-'),
            (None, '-')
        ]
        for raw_val, expected in cases:
            data = dict(
                title='Test',
                highlights='Test high',
                material='Madera',
                color=raw_val,
                medidas='10x20 cm',
                bullet_points=['B']*5,
                description='Desc',
                backend_keywords='kw'
            )
            parsed = generate.parse_ai_response(json.dumps(data))
            self.assertEqual(parsed['color'], expected)

    def test_incomplete_response(self):
        for raw in ['', '{"title": "Mesa"', '{"title":"Mesa", "bullet_points":42}', 'title: Mesa']:
            with self.subTest(raw=raw), self.assertRaises(ValueError): generate.parse_ai_response(raw)

    def test_visual_identification_required(self):
        listing = dict(title='Adorno de pared con forma de pez', highlights='Forma de pez',
                       bullet_points=['Detalle']*5, description='Adorno para colgar')
        for visual in [None, {}, {'status':'identified'},
                       {'status':'identified','object':'Pez','visible_features':[]},
                       {'status':'identified','object':'Pez','visible_features':[42]}]:
            with self.subTest(visual=visual), self.assertRaises(ValueError):
                generate.parse_ai_response(json.dumps(dict(listing,visual_analysis=visual)), require_visual=True)
        listing['visual_analysis'] = {'status':'identified','object':'Adorno de pared',
                                      'visible_features':['Forma de pez','Lazo para colgar']}
        result = generate.parse_ai_response(json.dumps(listing), require_visual=True)
        self.assertEqual(result['title'], listing['title'])

    def test_visual_abstention_without_listing(self):
        for status, message in [('unavailable','no pudo ver'),('uncertain','con claridad'),
                                ('conflict','productos distintos')]:
            with self.subTest(status=status), self.assertRaisesRegex(ValueError,message):
                generate.parse_ai_response(json.dumps({'visual_analysis':{'status':status}}), require_visual=True)

    def test_generation_does_not_truncate_size_or_material(self):
        row=dict(title='Adorno de pared de jacinto de agua 30x22 cm',highlights='Forma de pez',
                 bullet_points=['Detalle']*5,description='Adorno',
                 visual_analysis={'status':'identified','object':'Adorno de pared','visible_features':['Forma de pez']})
        self.assertEqual(generate.parse_ai_response(json.dumps(row),require_visual=True)['title'],row['title'])
        for field, value in [('title','Adorno de pared ' * 6 + '30 cm'),('highlights','Decoración ' * 13 + 'Jacinto de agua')]:
            with self.subTest(field=field), self.assertRaisesRegex(ValueError,'reformular'):
                generate.parse_ai_response(json.dumps(dict(row,**{field:value})),require_visual=True)

    def test_deepseek_reasoning_and_json_cleaning(self):
        raw_output = """<think>
        Visual analysis:
        { "temp_step": 1 }
        </think>
        ```json
        {
          "visual_analysis": {"status": "identified", "object": "Florero", "visible_features": ["cerámica blanco"]},
          "title": "Florero de Cerámica Blanco 15 cm",
          "highlights": "Florero decorativo",
          "material": "Cerámica",
          "color": "Blanco",
          "medidas": "15 cm",
          "bullet_points": ["Bullet 1", "Bullet 2", "Bullet 3", "Bullet 4", "Bullet 5",],
          "description": "Línea 1
Línea 2 con salto",
          "product_type": "Florero",
          "node_search_terms": ["florero"],
          "backend_keywords": "florero blanco"
        }
        ```"""
        parsed = generate.parse_ai_response(raw_output, require_visual=True)
        self.assertEqual(parsed['title'], "Florero de Cerámica Blanco 15 cm")
        self.assertEqual(len(parsed['bullet_points']), 5)
        self.assertIn("Línea 1", parsed['description'])

    def test_every_provider_sends_image_with_visual_title_prompt(self):
        data = {'content':[{'text':'result'}], 'choices':[{'message':{'content':'result'}}],
                'candidates':[{'content':{'parts':[{'text':'result'}]}}],
                'output':{'choices':[{'message':{'content':[{'text':'result'}]}}]}}
        for provider, fn in generate.PROVIDERS.items():
            response = MagicMock()
            response.__enter__.return_value.read.return_value = json.dumps(data).encode()
            with self.subTest(provider=provider), patch.object(generate.urllib.request,'urlopen',return_value=response) as opener, patch.object(generate,'fetch_image_b64',return_value=('image/png','test-image-bytes')):
                fn('key','https://example.com/product.jpg',name='Adorno proveedor')
                body=json.loads(opener.call_args.args[0].data)
                if provider == 'gemini':
                    parts=body['contents'][0]['parts']
                    self.assertTrue(any(p.get('inline_data',p.get('inlineData',{})).get('data')=='test-image-bytes' for p in parts))
                else:
                    messages=body.get('messages',body.get('input',{}).get('messages',[]))
                    parts=messages[0]['content']
                    self.assertTrue(any(p.get('image')=='https://example.com/product.jpg'
                                        or p.get('image_url',{}).get('url')=='https://example.com/product.jpg'
                                        or p.get('source',{}).get('url')=='https://example.com/product.jpg' for p in parts))
                prompt=' '.join(p.get('text','') for p in parts)
                self.assertIn('IDENTIFICACIÓN VISUAL OBLIGATORIA',prompt)
                self.assertIn('Adorno proveedor',prompt)
                self.assertIn('visual_analysis',prompt)

    def test_private_targets(self):
        for url in ['file:///etc/passwd','http://user:pass@example.com/a','http://127.0.0.1/a','http://[::1]/a','http://169.254.169.254/a']:
            with self.subTest(url=url), self.assertRaises(ValueError): generate.validate_image_url(url)

    def test_dns_mixed_addresses(self):
        with patch.object(generate.socket,'getaddrinfo',return_value=[(2,1,6,'',('8.8.8.8',443)),(2,1,6,'',('127.0.0.1',443))]):
            with self.assertRaises(ValueError): generate.validate_image_url('https://example.com/a')

    def test_gemini_pro(self):
        response=MagicMock()
        response.__enter__.return_value.read.return_value=json.dumps({'candidates':[{'content':{'parts':[{'text':'hidden','thought':True},{'text':'one'},{'text':'two'}]}}]}).encode()
        with patch.object(generate,'fetch_image_b64',return_value=('image/png','abc')),patch.object(generate.urllib.request,'urlopen',return_value=response) as opener:
            self.assertEqual(generate.call_gemini('test-secret','https://example.com/a',model='gemini-2.5-pro'),'onetwo')
            req=opener.call_args.args[0]
            self.assertNotIn('test-secret',req.full_url)
            self.assertEqual(req.get_header('X-goog-api-key'),'test-secret')
            self.assertGreater(json.loads(req.data)['generationConfig']['thinkingConfig']['thinkingBudget'],0)

    def test_provider_payloads(self):
        response=MagicMock()
        response.__enter__.return_value.read.return_value=json.dumps({'choices':[{'message':{'content':'result'}}]}).encode()
        for fn, expected in [(generate.call_deepseek,'deepseek-flash'),(generate.call_huggingface,'Qwen/Qwen2.5-VL-3B-Instruct')]:
            with self.subTest(provider=fn.__name__),patch.object(generate.urllib.request,'urlopen',return_value=response) as opener,patch.dict(generate.os.environ,{},clear=True):
                self.assertEqual(fn('key','https://example.com/a'),'result')
                req=opener.call_args.args[0]
                body=json.loads(req.data)
                self.assertEqual(body['model'],expected)
                self.assertEqual(body['messages'][0]['content'][1]['type'],'image_url')
                self.assertGreaterEqual(body['max_tokens'],2048)
                if fn is generate.call_deepseek:
                    self.assertEqual(req.full_url, 'https://api.deepseek.com/chat/completions')
                    self.assertEqual(req.get_header('Authorization'), 'Bearer key')
                    self.assertEqual(body['reasoning_effort'], 'none')
                    self.assertNotIn('reasoning', body)

    def test_image_redirect_private(self):
        conn=MagicMock()
        conn.getresponse.return_value.status=302
        conn.getresponse.return_value.getheader.return_value='http://127.0.0.1/private'
        with patch.object(generate,'validate_image_url',side_effect=[(generate.urllib.parse.urlsplit('http://example.com/a'),'8.8.8.8'),ValueError('private')]),patch.object(generate.http.client,'HTTPConnection',return_value=conn),patch.object(generate.socket,'create_connection'):
            with self.assertRaises(ValueError):generate.fetch_image_b64('http://example.com/a')
            conn.close.assert_called()

    def test_image_limits(self):
        for mime, data in [('text/html',b'<html>'),('image/png',b''),('image/png',b'a'*(generate.MAX_IMAGE_BYTES+1))]:
            conn=MagicMock();resp=conn.getresponse.return_value
            resp.status=200;resp.getheader.return_value=mime;resp.read.return_value=data
            with self.subTest(mime=mime,size=len(data)),patch.object(generate,'validate_image_url',return_value=(generate.urllib.parse.urlsplit('http://example.com/a'),'8.8.8.8')),patch.object(generate.http.client,'HTTPConnection',return_value=conn),patch.object(generate.socket,'create_connection'):
                with self.assertRaises(ValueError):generate.fetch_image_b64('http://example.com/a')
                conn.close.assert_called()

class HTTPTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server=ThreadingHTTPServer(('127.0.0.1',0),Handler)
        cls.thread=threading.Thread(target=cls.server.serve_forever,daemon=True)
        cls.thread.start()
        cls.base=f'http://127.0.0.1:{cls.server.server_port}'
    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown();cls.server.server_close();cls.thread.join()
    def request(self,path,body=None,headers=None):
        try:
            with urllib.request.urlopen(urllib.request.Request(self.base+path,data=body,headers=headers or {})) as resp: return resp.status,resp.read()
        except urllib.error.HTTPError as e: return e.code,e.read()
    def test_static_allowlist(self):
        for path in ['/','/index.html','/amazon-titulos.html','/app.js']: self.assertEqual(self.request(path)[0],200)
        for path in ['/.env','/server.py','/.git/config','/api/generate.py','/%2eenv']: self.assertEqual(self.request(path)[0],404)
    def test_invalid_json(self):
        for body in [b'{',b'[]',b'null',b'{"provider": []}']:
            status,data=self.request('/api/generate',body,{'Content-Type':'application/json'})
            self.assertEqual(status,400);self.assertIn('error',json.loads(data))
    def test_cross_origin(self):
        self.assertEqual(self.request('/api/save',b'{}',{'Content-Type':'application/json','Origin':'https://evil.example'})[0],403)
    def test_path_traversal(self):
        for filename in ['../escape.csv','/tmp/escape.csv','.hidden.csv','a/b.csv']:
            self.assertEqual(self.request('/api/save',json.dumps({'filename':filename,'content':'test'}).encode(),{'Content-Type':'application/json'})[0],400)
    def test_valid_generation(self):
        data=dict(title='Mesa',highlights='Uso interior',material='-',medidas='-',bullet_points=['Uno']*5,description='Una mesa')
        data['visual_analysis']={'status':'identified','object':'Mesa','visible_features':['Tablero y cuatro patas']}
        with patch.object(generate,'validate_image_url'),patch.dict(generate.PROVIDERS,{'test':lambda **kw:json.dumps(data)}):
            status,result=self.request('/api/generate',json.dumps({'provider':'test','api_key':'test-key','image_url':'https://example.com/a','dimensions':'1x2 m'}).encode(),{'Content-Type':'application/json'})
            self.assertEqual(status,200);self.assertEqual(json.loads(result)['medidas'],'100x200 cm')

    def test_generation_does_not_accept_text_without_visual_analysis(self):
        for data in [{'title':'Mesa','highlights':'Uso interior','bullet_points':['Uno']*5,'description':'Mesa'},
                     {'visual_analysis':{'status':'unavailable'}}]:
            with self.subTest(data=data), patch.object(generate,'validate_image_url'), patch.dict(generate.PROVIDERS,{'test':lambda **kw:json.dumps(data)}):
                status,result=self.request('/api/generate',json.dumps({'provider':'test','api_key':'test-key','image_url':'https://example.com/a'}).encode(),{'Content-Type':'application/json'})
                self.assertEqual(status,400)
                self.assertIn('error',json.loads(result))
                self.assertNotIn('title',json.loads(result))

    def test_host_rebinding(self):
        self.assertEqual(self.request('/api/save',b'{}',{'Content-Type':'application/json','Host':'evil.example'})[0],403)

    def test_save_and_collision(self):
        import tempfile
        from pathlib import Path
        with tempfile.TemporaryDirectory() as folder,patch('server.os.path.expanduser',return_value=folder):
            body=json.dumps({'filename':'test.csv','content':'Título,Medidas'}).encode()
            self.assertEqual(self.request('/api/save',body,{'Content-Type':'application/json'})[0],200)
            self.assertEqual((Path(folder)/'Downloads/test.csv').read_text(encoding='utf-8-sig'),'Título,Medidas')
            self.assertEqual(self.request('/api/save',body,{'Content-Type':'application/json'})[0],409)

    def test_public_key_not_used(self):
        with patch.dict(generate.os.environ,{'VERCEL':'1','ALLOW_SERVER_API_KEYS':'0','GEMINI_API_KEY':'must-not-use'}):
            status,body=self.request('/api/generate',b'{"image_url":"https://example.com/a"}',{'Content-Type':'application/json'})
            self.assertEqual(status,400)
            self.assertNotIn(b'must-not-use',body)

    def test_map_node_action(self):
        def provider(**kw):
            self.assertIn('candidatos_excel', kw['prompt_override'])
            return json.dumps({'node_id':'2844384031','confidence':'alta','reason':'Es un jarrón decorativo'})
        with patch.object(generate,'validate_image_url'), patch.dict(generate.PROVIDERS,{'test':provider}):
            status, body=self.request('/api/generate',json.dumps({'action':'map_node','provider':'test','api_key':'key','image_url':'https://example.com/a','listing':{'title':'Jarrón de cerámica'}}).encode(),{'Content-Type':'application/json'})
            self.assertEqual(status,200)
            self.assertEqual(json.loads(body)['node_id'],'2844384031')
            self.assertNotIn('title',json.loads(body))

    def test_search_catalog_without_api_key(self):
        status, body=self.request('/api/generate',b'{"action":"search_nodes","query":"2844384031"}',{'Content-Type':'application/json'})
        self.assertEqual(status,200)
        self.assertEqual(json.loads(body)['nodes'][0]['id'],'2844384031')

    def test_export_bulk_action(self):
        import base64, io, openpyxl
        payload = {
            'action': 'export_bulk',
            'supplier': 'signes',
            'items': [
                {
                    'ref': '12345',
                    'url': 'https://example.com/images/jarron123.jpg',
                    'title': 'Jarrón nórdico blanco',
                    'highlights': 'Cerámica blanca, acabado mate',
                    'node_id': '2844384031',
                    'description': 'Elegante jarrón para decoración nórdica de salones.',
                    'bullet_points': ['Punto 1', 'Punto 2', 'Punto 3', 'Punto 4', 'Punto 5'],
                    'material': 'Cerámica',
                    'color': 'Blanco',
                    'medidas': '25x12x12 cm',
                    'backend_keywords': 'florero jarron decoracion salon nordico diseno minimalista mesa centro regalo'
                },
                {
                    'ref': '98765SGI',
                    'image_url': 'https://example.com/images/alfombra987.jpg',
                    'title': 'Alfombrilla antideslizante',
                    'highlights': 'Fácil limpieza, resistente',
                    'node_id': '3244794031',
                    'description': 'Alfombra de baño de microfibra de secado rápido.',
                    'bullet_points': ['Bullet A', 'Bullet B', 'Bullet C', 'Bullet D', 'Bullet E'],
                    'material': 'Microfibra',
                    'color': 'Multicolor',
                    'medidas': '60x40 cm',
                    'backend_keywords': 'alfombra bano antideslizante suelo ducha suave absorbente'
                }
            ]
        }
        status, body = self.request('/api/generate', json.dumps(payload).encode(), {'Content-Type': 'application/json'})
        self.assertEqual(status, 200)
        data = json.loads(body)
        self.assertEqual(data['count'], 2)
        self.assertTrue(data['filename'].endswith('.xlsm'))

        wb = openpyxl.load_workbook(io.BytesIO(base64.b64decode(data['content_b64'])), keep_vba=True)
        self.assertNotIn('Explorar datos', wb.sheetnames)
        for sname in wb.sheetnames:
            self.assertNotIn('nodo', sname.lower())
            self.assertNotIn('explor', sname.lower())
        ws = wb['Plantilla']
        # Fila 7: Producto 1
        self.assertEqual(ws['A7'].value, '12345SGI')
        self.assertEqual(ws['B7'].value, 'Home')
        self.assertEqual(ws['C7'].value, 'Crear o reemplazar (actualización completa)')
        self.assertEqual(ws['G7'].value, 'Jarrón nórdico blanco')
        self.assertEqual(ws['H7'].value, 'Cerámica blanca, acabado mate')
        self.assertEqual(ws['I7'].value, 'ROCKING GIFTS')
        self.assertEqual(ws['J7'].value, 'EAN')
        self.assertEqual(ws['L7'].value, '2844384031')
        self.assertEqual(ws['Q7'].value, 'Unidad')
        self.assertEqual(ws['R7'].value, 1)
        self.assertEqual(ws['T7'].value, ws['A7'].value)
        self.assertEqual(ws['U7'].value, ws['I7'].value)
        self.assertEqual(ws['X7'].value, 'https://example.com/images/jarron123.jpg')
        self.assertEqual(ws['AG7'].value, 'https://example.com/images/jarron123.jpg')
        self.assertEqual(ws['AN7'].value, 'Elegante jarrón para decoración nórdica de salones.')
        self.assertEqual(ws['AO7'].value, 'Punto 1')
        self.assertEqual(ws['AP7'].value, 'Punto 2')
        self.assertEqual(ws['AQ7'].value, 'Punto 3')
        self.assertEqual(ws['AR7'].value, 'Punto 4')
        self.assertEqual(ws['AS7'].value, 'Punto 5')
        self.assertEqual(ws['AT7'].value, 'florero jarron decoracion salon nordico diseno minimalista mesa centro regalo')
        self.assertEqual(ws['AV7'].value, 'Cerámica')
        self.assertEqual(ws['BD7'].value, 'Blanco')
        self.assertEqual(ws['BE7'].value, '25x12x12 cm')
        self.assertEqual(ws['DQ7'].value, 12)
        self.assertEqual(ws['DR7'].value, 'Centímetros')
        self.assertEqual(ws['DS7'].value, 25)
        self.assertEqual(ws['DT7'].value, 'Centímetros')
        self.assertEqual(ws['DU7'].value, 12)
        self.assertEqual(ws['DV7'].value, 'Centímetros')
        self.assertEqual(ws['EF7'].value, 'Nuevo')
        self.assertEqual(ws['FH7'].value, 2)
        self.assertEqual(ws['FO7'].value, '2035-12-31')
        self.assertEqual(ws['FP7'].value, '2026-08-01')
        self.assertEqual(ws['GJ7'].value, 'ENVIO 4')
        self.assertEqual(ws['JU7'].value, 'España')
        self.assertEqual(ws['JV7'].value, 'No')
        self.assertEqual(ws['MH7'].value, 'Sí')
        self.assertEqual(ws['MI7'].value, 'vidalregals@gmail.com')

        # Fila 8: Producto 2 (no duplicar SGI si ya lo trae)
        self.assertEqual(ws['A8'].value, '98765SGI')
        self.assertEqual(ws['B8'].value, 'Home')
        self.assertEqual(ws['C8'].value, 'Crear o reemplazar (actualización completa)')
        self.assertEqual(ws['G8'].value, 'Alfombrilla antideslizante')
        self.assertEqual(ws['H8'].value, 'Fácil limpieza, resistente')
        self.assertEqual(ws['I8'].value, 'ROCKING GIFTS')
        self.assertEqual(ws['J8'].value, 'EAN')
        self.assertEqual(ws['L8'].value, '3244794031')
        self.assertEqual(ws['Q8'].value, 'Unidad')
        self.assertEqual(ws['R8'].value, 1)
        self.assertEqual(ws['T8'].value, ws['A8'].value)
        self.assertEqual(ws['U8'].value, ws['I8'].value)
        self.assertEqual(ws['X8'].value, 'https://example.com/images/alfombra987.jpg')
        self.assertEqual(ws['AG8'].value, 'https://example.com/images/alfombra987.jpg')
        self.assertEqual(ws['AN8'].value, 'Alfombra de baño de microfibra de secado rápido.')
        self.assertEqual(ws['AO8'].value, 'Bullet A')
        self.assertEqual(ws['AP8'].value, 'Bullet B')
        self.assertEqual(ws['AQ8'].value, 'Bullet C')
        self.assertEqual(ws['AR8'].value, 'Bullet D')
        self.assertEqual(ws['AS8'].value, 'Bullet E')
        self.assertEqual(ws['AT8'].value, 'alfombra bano antideslizante suelo ducha suave absorbente')
        self.assertEqual(ws['AV8'].value, 'Microfibra')
        self.assertEqual(ws['BD8'].value, 'Multicolor')
        self.assertEqual(ws['BE8'].value, '60x40 cm')
        self.assertEqual(ws['DQ8'].value, 1)
        self.assertEqual(ws['DR8'].value, 'Centímetros')
        self.assertEqual(ws['DS8'].value, 60)
        self.assertEqual(ws['DT8'].value, 'Centímetros')
        self.assertEqual(ws['DU8'].value, 40)
        self.assertEqual(ws['DV8'].value, 'Centímetros')
        self.assertEqual(ws['EF8'].value, 'Nuevo')
        self.assertEqual(ws['FH8'].value, 2)
        self.assertEqual(ws['FO8'].value, '2035-12-31')
        self.assertEqual(ws['FP8'].value, '2026-08-01')
        self.assertEqual(ws['GJ8'].value, 'ENVIO 4')
        self.assertEqual(ws['JU8'].value, 'España')
        self.assertEqual(ws['JV8'].value, 'No')
        self.assertEqual(ws['MH8'].value, 'Sí')
        self.assertEqual(ws['MI8'].value, 'vidalregals@gmail.com')

    def test_divisor_prompt_and_pack_title(self):
        # 1. Prompt divisor=1 vs divisor=2
        p1 = generate.build_prompt("Adorno pez", "30 cm", divisor=1)
        self.assertNotIn("UNIDADES DEL PACK / DIVISOR", p1)
        self.assertNotIn("PACK / MULTIPLICADOR OBLIGATORIO", p1)

        p2 = generate.build_prompt("Adorno pez", "30 cm", divisor=2)
        self.assertIn("CANTIDAD DEL PACK / DIVISOR: 2 unidades", p2)
        self.assertIn("x2", p2)
        self.assertIn("PACK DE 2 UNIDADES", p2)

        # 2. ensure_pack_in_title helper
        title1 = "Adorno de pared Pez de mimbre 30 cm"
        self.assertEqual(generate.ensure_pack_in_title(title1, divisor=1), title1)
        self.assertEqual(generate.ensure_pack_in_title(title1, divisor=2), "Adorno de pared x2 Pez de mimbre 30 cm")

        # Already has x2
        title2 = "Adorno de pared x2 Pez de mimbre 30 cm"
        self.assertEqual(generate.ensure_pack_in_title(title2, divisor=2), title2)

        # Max length <= 75 chars
        long_title = "Adorno de pared de fibra natural pez de mimbre decoracion salon comedor 30x20 cm"
        res_title = generate.ensure_pack_in_title(long_title, divisor=3)
        self.assertIn("x3", res_title)
        self.assertLessEqual(len(res_title), 75)

    def test_divisor_bulk_import(self):
        from api._bulk_import import generate_bulk_import_excel
        import io, openpyxl
        item = {
            "sku": "12345SGI",
            "title": "Adorno x2",
            "divisor": 2,
            "highlights": "Pack de 2 piezas",
            "bullet_points": ["B1", "B2", "B3", "B4", "B5"],
            "description": "Pack de 2 unidades",
            "node_id": "123"
        }
        excel_bytes = generate_bulk_import_excel([item])
        wb = openpyxl.load_workbook(io.BytesIO(excel_bytes), data_only=True)
        ws = wb["Plantilla"]
        # Row 7 is first item row
        self.assertEqual(ws['R7'].value, 2)
        self.assertEqual(ws['BA7'].value, 2)

if __name__=='__main__': unittest.main()
