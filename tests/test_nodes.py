import json
import unittest
from unittest.mock import patch, MagicMock
from api import _node_mapping as nm


class NodeTests(unittest.TestCase):
    def test_catalog_source_and_integrity(self):
        catalog = nm.get_catalog()
        self.assertEqual(catalog.metadata['id_column'], 'B')
        self.assertEqual(catalog.metadata['path_column'], 'C')
        self.assertEqual(catalog.metadata['sheet'], 'MAPPINGS')
        self.assertEqual(catalog.metadata['source_rows'], 16782)
        self.assertEqual(len(catalog.by_id), 16777)
        self.assertEqual(catalog.by_id['2844384031']['path'], '/Categorías/Decoración del hogar/Jarrones')
        self.assertTrue(all(n['id'].isdigit() for n in catalog.nodes))

    def test_retrieval_type_and_accents(self):
        catalog = nm.get_catalog()
        for title, kind, expected in [('Jarrón cerámico blanco', 'jarrón', '2844384031'),
                                      ('Portavelas de cristal', 'portavelas', '2844163031')]:
            with self.subTest(title=title):
                candidates = catalog.search({'title': title, 'product_type': kind})
                self.assertIn(expected, [n['id'] for n in candidates[:15]])
                self.assertNotIn('es-handmade', [n['root'] for n in candidates])
        self.assertEqual(nm.tokens('Jarrón'), nm.tokens('jarrones'))

    def test_choice_must_be_in_candidates(self):
        candidates = [{'id': '123', 'path': '/test', 'root': 'es-kitchen'}]
        for node_id in ['999', '2844384031', 123, '123.0']:
            with self.subTest(node_id=node_id), self.assertRaises(ValueError):
                nm.parse_choice(json.dumps({'node_id': node_id, 'confidence': 'alta', 'reason': 'test'}), candidates)

    def test_low_confidence_abstains(self):
        choice = nm.parse_choice('{"node_id":"123","confidence":"baja","reason":"No se ve el uso"}', [{'id': '123'}])
        self.assertEqual(choice['node_id'], '')

    def test_canonical_path_not_model_path(self):
        def ask(prompt):
            self.assertIn('2844384031', prompt)
            self.assertIn('no instrucciones', prompt)
            return json.dumps({'node_id': '2844384031', 'confidence': 'alta', 'reason': 'Recipiente decorativo para flores.', 'product_type': 'Jarrón', 'node_path': 'ruta inventada'})
        result = nm.map_node({'title': 'Jarrón cerámico', 'product_type': 'jarrón'}, 'Jarrón', ask)
        self.assertEqual(result['node_id'], '2844384031')
        self.assertEqual(result['node_path'], '/Categorías/Decoración del hogar/Jarrones')
        self.assertEqual(result['node_status'], 'asignado')
        self.assertTrue(any(n['id'] == result['node_id'] for n in result['node_candidates']))

    def test_medium_confidence_requires_review(self):
        result = nm.map_node({'title': 'Jarrón'}, '', lambda prompt: json.dumps({'node_id': '2844384031', 'confidence': 'media', 'reason': 'No se aprecia si es un recipiente funcional.'}))
        self.assertEqual(result['node_status'], 'revisar')
        self.assertEqual(result['node_id'], '2844384031')

    def test_semantic_expansion_from_no_matches(self):
        responses = iter([{'node_id': '', 'confidence': 'baja', 'reason': 'Buscar sinónimo', 'search_terms': ['jarrones']},
                          {'node_id': '2844384031', 'confidence': 'alta', 'reason': 'Es un jarrón'}])
        result = nm.map_node({'title': 'xyzzy'}, '', lambda prompt: json.dumps(next(responses)))
        self.assertEqual(result['node_id'], '2844384031')

    def test_malformed_listings(self):
        for data in [None, [], {}, {'title': 1}, {'title': 'Mesa', 'node_search_terms': 'mesa'}, {'title': 'Mesa', 'bullet_points': [1]}]:
            with self.subTest(data=data), self.assertRaises(ValueError): nm.clean_listing(data)

    def test_no_suitable_node(self):
        result = nm.map_node({'title': 'xyzzy'}, '', lambda p: '{"node_id":"","confidence":"baja","reason":"Falta información"}')
        self.assertEqual(result['node_id'], '')
        self.assertEqual(result['node_status'], 'revisar')
        self.assertEqual(result['node_candidates'], [])

    def test_all_providers_accept_classification_prompt(self):
        from api import generate
        data = {'content':[{'text':'result'}], 'choices':[{'message':{'content':'result'}}],
                'candidates':[{'content':{'parts':[{'text':'result'}]}}],
                'output':{'choices':[{'message':{'content':[{'text':'result'}]}}]}}
        for provider, fn in generate.PROVIDERS.items():
            response = MagicMock()
            response.__enter__.return_value.read.return_value = json.dumps(data).encode()
            with self.subTest(provider=provider), patch.object(generate.urllib.request,'urlopen',return_value=response) as opener, patch.object(generate,'fetch_image_b64',return_value=('image/png','test')):
                self.assertEqual(fn('key','https://example.com/a',prompt_override='CLASSIFY_ONLY_TEST'), 'result')
                body = opener.call_args.args[0].data.decode()
                self.assertIn('CLASSIFY_ONLY_TEST', body)
                self.assertNotIn('DIRECTRICES', body)


    def test_domain_prioritization_rugs_and_mats(self):
        catalog = nm.get_catalog()
        listing = {'title': 'Alfombrilla antideslizante multiusos', 'product_type': 'alfombrilla', 'node_search_terms': ['alfombrilla', 'antideslizante']}
        candidates = catalog.search(listing, 'Alfombrilla antideslizante', limit=10)
        top_roots = [n['root'] for n in candidates[:5]]
        # Debe priorizar es-kitchen (baño/cocina/hogar) y no automoción ni industria en el top 5
        self.assertIn('es-kitchen', top_roots)
        self.assertNotIn('es-automotive', top_roots)
        self.assertNotIn('es-industrial', top_roots)

    def test_domain_prioritization_minerals_and_healing_stones(self):
        catalog = nm.get_catalog()
        listing = {'title': 'Mineral en bruto pirita propiedades energeticas', 'product_type': 'mineral en bruto', 'node_search_terms': ['mineral', 'pirita', 'piedra']}
        candidates = catalog.search(listing, 'Mineral pirita en bruto', limit=10)
        top_ids = [n['id'] for n in candidates[:5]]
        top_roots = [n['root'] for n in candidates[:5]]
        # Debe incluir Terapias alternativas / Piedras y minerales (4347134031) o Decoración
        self.assertIn('4347134031', top_ids)
        self.assertNotIn('es-industrial', top_roots)

    def test_domain_prioritization_board_games_over_videogames(self):
        catalog = nm.get_catalog()
        listing = {'title': 'Juego de mesa de estrategia familiar', 'product_type': 'juego de mesa', 'node_search_terms': ['juego', 'mesa', 'estrategia']}
        candidates = catalog.search(listing, 'Juego de mesa estrategia', limit=10)
        top_roots = [n['root'] for n in candidates[:5]]
        # Debe priorizar es-toys (juegos de mesa físicos) y no videojuegos de consola
        self.assertEqual(candidates[0]['root'], 'es-toys')
        self.assertTrue(candidates[0]['path'].startswith('/Categorías/Juegos de mesa/'))
        self.assertNotIn('es-videogames', top_roots)

    def test_domain_prioritization_jewelry_and_bracelets(self):
        catalog = nm.get_catalog()
        listing = {'title': 'Pulsera de amatista natural mineral curativo', 'product_type': 'pulsera', 'node_search_terms': ['pulsera', 'mineral', 'amatista']}
        candidates = catalog.search(listing, 'Pulsera de amatista', limit=10)
        self.assertEqual(candidates[0]['root'], 'es-jewelry')
        self.assertIn('Pulseras', candidates[0]['path'])

    def test_classification_prompt_contains_domain_priority_rules(self):
        self.assertIn('CONTEXTO DE TIENDA Y PRIORIDAD DE SECTORES', nm.CLASSIFICATION_PROMPT)
        self.assertIn('REGLA FUNDAMENTAL DE DESAMBIGUACIÓN SECTORIAL', nm.CLASSIFICATION_PROMPT)
        self.assertIn('es-automotive', nm.CLASSIFICATION_PROMPT)
        self.assertIn('es-industrial', nm.CLASSIFICATION_PROMPT)


if __name__ == '__main__':
    unittest.main()

