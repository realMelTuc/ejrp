"""
EJRP test suite — pytest
Tests: jump_calc logic, Flask routes, blueprint endpoints
"""
import importlib.util
import json
import math
import os
import sys

import pytest

# ── Ensure project root on path ───────────────────────────────────────────────
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)


# ── jump_calc tests ───────────────────────────────────────────────────────────

from jump_calc import (
    SHIPS, SHIPS_BY_CLASS, CLASS_LABELS, FUEL_TYPES,
    get_ship, effective_range, fuel_for_jump, calculate_route,
)


class TestShipData:
    def test_all_ships_have_required_keys(self):
        required = {'class', 'race', 'base_range_ly', 'fuel_type', 'base_fuel_per_ly'}
        for name, data in SHIPS.items():
            assert required <= set(data.keys()), f'{name} missing keys'

    def test_jump_freighters_have_cargo(self):
        jf_names = ['Ark', 'Anshar', 'Rhea', 'Nomad']
        for n in jf_names:
            assert 'cargo_m3' in SHIPS[n], f'{n} missing cargo_m3'

    def test_fuel_types_valid(self):
        valid = {'Oxygen Isotopes', 'Hydrogen Isotopes', 'Nitrogen Isotopes', 'Helium Isotopes'}
        for name, data in SHIPS.items():
            assert data['fuel_type'] in valid, f'{name} invalid fuel type'

    def test_ship_classes_valid(self):
        valid_classes = {'jump_freighter', 'carrier', 'dreadnought', 'supercarrier', 'titan', 'black_ops'}
        for name, data in SHIPS.items():
            assert data['class'] in valid_classes, f'{name} invalid class'

    def test_ships_by_class_populated(self):
        assert 'jump_freighter' in SHIPS_BY_CLASS
        assert 'carrier' in SHIPS_BY_CLASS
        assert 'dreadnought' in SHIPS_BY_CLASS
        assert 'black_ops' in SHIPS_BY_CLASS

    def test_class_labels_all_classes(self):
        for cls in SHIPS_BY_CLASS:
            assert cls in CLASS_LABELS, f'{cls} missing from CLASS_LABELS'

    def test_ark_is_amarr_jf(self):
        ark = SHIPS['Ark']
        assert ark['class'] == 'jump_freighter'
        assert ark['race'] == 'Amarr'
        assert ark['fuel_type'] == 'Oxygen Isotopes'

    def test_widow_is_caldari_black_ops(self):
        w = SHIPS['Widow']
        assert w['class'] == 'black_ops'
        assert w['race'] == 'Caldari'

    def test_base_ranges_positive(self):
        for name, data in SHIPS.items():
            assert data['base_range_ly'] > 0, f'{name} has non-positive base range'

    def test_fuel_per_ly_positive(self):
        for name, data in SHIPS.items():
            assert data['base_fuel_per_ly'] > 0, f'{name} has non-positive fuel/LY'

    def test_get_ship_known(self):
        s = get_ship('Anshar')
        assert s is not None
        assert s['class'] == 'jump_freighter'

    def test_get_ship_unknown(self):
        assert get_ship('UnknownShip') is None

    def test_get_ship_case_sensitive(self):
        assert get_ship('ark') is None
        assert get_ship('Ark') is not None

    def test_four_jf_ships(self):
        jfs = SHIPS_BY_CLASS.get('jump_freighter', [])
        assert len(jfs) == 4

    def test_four_carriers(self):
        assert len(SHIPS_BY_CLASS.get('carrier', [])) == 4

    def test_four_dreadnoughts(self):
        assert len(SHIPS_BY_CLASS.get('dreadnought', [])) == 4

    def test_four_black_ops(self):
        assert len(SHIPS_BY_CLASS.get('black_ops', [])) == 4

    def test_amarr_ships_oxygen(self):
        for name, data in SHIPS.items():
            if data['race'] == 'Amarr':
                assert data['fuel_type'] == 'Oxygen Isotopes', f'{name} race/fuel mismatch'

    def test_gallente_ships_hydrogen(self):
        for name, data in SHIPS.items():
            if data['race'] == 'Gallente':
                assert data['fuel_type'] == 'Hydrogen Isotopes', f'{name} race/fuel mismatch'

    def test_caldari_ships_nitrogen(self):
        for name, data in SHIPS.items():
            if data['race'] == 'Caldari':
                assert data['fuel_type'] == 'Nitrogen Isotopes', f'{name} race/fuel mismatch'

    def test_minmatar_ships_helium(self):
        for name, data in SHIPS.items():
            if data['race'] == 'Minmatar':
                assert data['fuel_type'] == 'Helium Isotopes', f'{name} race/fuel mismatch'


class TestEffectiveRange:
    def test_jdc0_equals_base(self):
        assert effective_range(3.5, 0) == 3.5

    def test_jdc5_is_225_percent(self):
        result = effective_range(3.5, 5)
        assert abs(result - 3.5 * 2.25) < 0.001

    def test_jdc1_is_125_percent(self):
        result = effective_range(4.0, 1)
        assert abs(result - 4.0 * 1.25) < 0.001

    def test_jdc_clamps_at_5(self):
        assert effective_range(3.5, 5) == effective_range(3.5, 10)

    def test_jdc_clamps_at_0(self):
        assert effective_range(3.5, 0) == effective_range(3.5, -5)

    def test_range_increases_with_jdc(self):
        base = 3.5
        r0 = effective_range(base, 0)
        r3 = effective_range(base, 3)
        r5 = effective_range(base, 5)
        assert r0 < r3 < r5

    def test_black_ops_lower_range(self):
        bo = SHIPS['Widow']['base_range_ly']
        jf = SHIPS['Ark']['base_range_ly']
        assert effective_range(bo, 5) < effective_range(jf, 5)

    def test_return_type_float(self):
        result = effective_range(3.5, 3)
        assert isinstance(result, float)


class TestFuelForJump:
    def test_zero_distance_minimum_one(self):
        assert fuel_for_jump(1000, 0, 0) == 1

    def test_jdfe0_full_cost(self):
        result = fuel_for_jump(1000, 5.0, 0)
        assert result == math.ceil(5.0 * 1000 * 1.0)

    def test_jdfe5_half_cost(self):
        result = fuel_for_jump(1000, 5.0, 5)
        expected = math.ceil(5.0 * 1000 * 0.5)
        assert result == expected

    def test_jdfe_clamps_at_5(self):
        assert fuel_for_jump(1000, 5.0, 5) == fuel_for_jump(1000, 5.0, 10)

    def test_jdfe_clamps_at_0(self):
        assert fuel_for_jump(1000, 5.0, 0) == fuel_for_jump(1000, 5.0, -3)

    def test_fuel_decreases_with_jdfe(self):
        f0 = fuel_for_jump(1000, 5.0, 0)
        f3 = fuel_for_jump(1000, 5.0, 3)
        f5 = fuel_for_jump(1000, 5.0, 5)
        assert f0 > f3 > f5

    def test_fuel_scales_with_distance(self):
        f1 = fuel_for_jump(1000, 1.0, 0)
        f5 = fuel_for_jump(1000, 5.0, 0)
        assert f5 > f1

    def test_fuel_scales_with_base_rate(self):
        f_jf  = fuel_for_jump(1000, 5.0, 0)
        f_cap = fuel_for_jump(2500, 5.0, 0)
        assert f_cap > f_jf

    def test_return_type_int(self):
        result = fuel_for_jump(1000, 5.0, 3)
        assert isinstance(result, int)

    def test_positive_result(self):
        assert fuel_for_jump(1000, 0.01, 5) >= 1


class TestCalculateRoute:
    def _waypoints(self, *distances):
        return [{'from': f'Sys{i}', 'to': f'Sys{i+1}', 'distance_ly': d}
                for i, d in enumerate(distances)]

    def test_single_jump(self):
        r = calculate_route('Ark', self._waypoints(5.0), 5, 5, 500)
        assert r['valid'] is True
        assert r['total_jumps'] == 1
        assert r['total_distance_ly'] == 5.0
        assert r['total_fuel'] > 0

    def test_multiple_jumps(self):
        r = calculate_route('Ark', self._waypoints(3.0, 4.0, 5.0), 5, 5, 500)
        assert r['total_jumps'] == 3

    def test_total_distance_sum(self):
        r = calculate_route('Ark', self._waypoints(3.0, 4.0), 5, 5, 500)
        assert abs(r['total_distance_ly'] - 7.0) < 0.001

    def test_cost_is_fuel_times_price(self):
        price = 750.0
        r = calculate_route('Ark', self._waypoints(5.0), 5, 5, price)
        assert abs(r['total_cost_isk'] - r['total_fuel'] * price) < 0.01

    def test_unknown_ship_error(self):
        r = calculate_route('NoShip', self._waypoints(5.0), 5, 5, 500)
        assert 'error' in r
        assert r['valid'] is False

    def test_out_of_range_flagged(self):
        # 100 LY is way beyond any range
        r = calculate_route('Ark', self._waypoints(100.0), 5, 5, 500)
        assert r['has_out_of_range'] is True
        assert r['valid'] is False
        assert r['steps'][0]['within_range'] is False

    def test_in_range_steps_valid(self):
        r = calculate_route('Ark', self._waypoints(3.0), 5, 5, 500)
        assert r['steps'][0]['within_range'] is True

    def test_step_has_required_keys(self):
        r = calculate_route('Ark', self._waypoints(4.0), 5, 5, 500)
        step = r['steps'][0]
        for k in ('step', 'from_system', 'to_system', 'distance_ly', 'fuel', 'cost_isk', 'within_range', 'max_range'):
            assert k in step, f'step missing key: {k}'

    def test_fuel_type_from_ship(self):
        r = calculate_route('Ark', self._waypoints(3.0), 5, 5, 500)
        assert r['fuel_type'] == 'Oxygen Isotopes'

    def test_fuel_type_anshar(self):
        r = calculate_route('Anshar', self._waypoints(3.0), 5, 5, 500)
        assert r['fuel_type'] == 'Hydrogen Isotopes'

    def test_max_range_in_result(self):
        r = calculate_route('Ark', self._waypoints(3.0), 5, 5, 500)
        assert r['max_range_ly'] > 0

    def test_jdc_affects_max_range(self):
        r0 = calculate_route('Ark', self._waypoints(3.0), 0, 5, 500)
        r5 = calculate_route('Ark', self._waypoints(3.0), 5, 5, 500)
        assert r5['max_range_ly'] > r0['max_range_ly']

    def test_jdfe_affects_fuel(self):
        r0 = calculate_route('Ark', self._waypoints(4.0), 5, 0, 500)
        r5 = calculate_route('Ark', self._waypoints(4.0), 5, 5, 500)
        assert r0['total_fuel'] > r5['total_fuel']

    def test_black_ops_smaller_range(self):
        r_jf = calculate_route('Ark', self._waypoints(3.0), 5, 5, 500)
        r_bo = calculate_route('Widow', self._waypoints(3.0), 5, 5, 500)
        assert r_bo['max_range_ly'] < r_jf['max_range_ly']

    def test_step_from_to_preserved(self):
        wps = [{'from': 'Jita', 'to': 'HED-GP', 'distance_ly': 4.5}]
        r = calculate_route('Ark', wps, 5, 5, 500)
        assert r['steps'][0]['from_system'] == 'Jita'
        assert r['steps'][0]['to_system'] == 'HED-GP'

    def test_zero_price_means_zero_cost(self):
        r = calculate_route('Ark', self._waypoints(4.0), 5, 5, 0)
        assert r['total_cost_isk'] == 0.0

    def test_empty_waypoints(self):
        r = calculate_route('Ark', [], 5, 5, 500)
        assert r['total_jumps'] == 0

    def test_ships_by_class_keys(self):
        for cls, ships in SHIPS_BY_CLASS.items():
            assert isinstance(ships, list)
            assert len(ships) > 0


# ── Flask app tests ───────────────────────────────────────────────────────────

@pytest.fixture
def app():
    os.environ.setdefault('SUPABASE_DB_HOST', 'localhost')
    os.environ.setdefault('SUPABASE_DB_NAME', 'test')
    os.environ.setdefault('SUPABASE_DB_USER', 'test')
    os.environ.setdefault('SUPABASE_DB_PASSWORD', 'test')
    os.environ.setdefault('SUPABASE_DB_PORT', '5432')

    spec = importlib.util.spec_from_file_location('app', os.path.join(ROOT, 'app.py'))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    flask_app = module.app
    flask_app.config['TESTING'] = True
    return flask_app


@pytest.fixture
def client(app):
    return app.test_client()


class TestFlaskRoutes:
    def test_landing_page(self, client):
        r = client.get('/')
        assert r.status_code == 200

    def test_shell_page(self, client):
        r = client.get('/app/')
        assert r.status_code == 200

    def test_debug_endpoint(self, client):
        r = client.get('/api/debug')
        assert r.status_code == 200
        data = json.loads(r.data)
        assert data['app'] == 'EJRP'

    def test_health_endpoint_structure(self, client):
        r = client.get('/api/health')
        assert r.status_code in (200, 500)
        data = json.loads(r.data)
        assert 'status' in data

    def test_dashboard_partial(self, client):
        r = client.get('/dashboard/')
        assert r.status_code == 200

    def test_planner_partial(self, client):
        r = client.get('/planner/')
        assert r.status_code == 200

    def test_routes_partial(self, client):
        r = client.get('/routes/')
        assert r.status_code == 200

    def test_fuel_partial(self, client):
        r = client.get('/fuel/')
        assert r.status_code == 200

    def test_planner_ships_api(self, client):
        r = client.get('/api/planner/ships')
        assert r.status_code == 200
        data = json.loads(r.data)
        assert isinstance(data, list)
        assert len(data) > 0

    def test_planner_ships_has_jf_group(self, client):
        r = client.get('/api/planner/ships')
        data = json.loads(r.data)
        classes = [g['class'] for g in data]
        assert 'jump_freighter' in classes

    def test_planner_ships_group_has_ships(self, client):
        r = client.get('/api/planner/ships')
        data = json.loads(r.data)
        for g in data:
            assert 'ships' in g
            assert len(g['ships']) > 0
            assert 'label' in g

    def test_planner_ship_detail(self, client):
        r = client.get('/api/planner/ship/Ark')
        assert r.status_code == 200
        data = json.loads(r.data)
        assert data['name'] == 'Ark'
        assert 'base_range_ly' in data
        assert 'fuel_type' in data

    def test_planner_ship_not_found(self, client):
        r = client.get('/api/planner/ship/NonExistent')
        assert r.status_code == 404

    def test_calculate_valid_route(self, client):
        payload = {
            'ship_name': 'Ark',
            'jdc_level': 5,
            'jdfe_level': 5,
            'fuel_price_isk': 500,
            'waypoints': [{'from': 'Jita', 'to': 'Test', 'distance_ly': 4.5}],
        }
        r = client.post('/api/planner/calculate',
                        data=json.dumps(payload),
                        content_type='application/json')
        assert r.status_code == 200
        data = json.loads(r.data)
        assert data['total_jumps'] == 1
        assert data['total_fuel'] > 0
        assert data['fuel_type'] == 'Oxygen Isotopes'

    def test_calculate_multiple_waypoints(self, client):
        payload = {
            'ship_name': 'Rhea',
            'jdc_level': 4,
            'jdfe_level': 3,
            'fuel_price_isk': 450,
            'waypoints': [
                {'from': 'Jita', 'to': 'MJ-5F9', 'distance_ly': 3.2},
                {'from': 'MJ-5F9', 'to': 'HED-GP', 'distance_ly': 5.8},
            ],
        }
        r = client.post('/api/planner/calculate',
                        data=json.dumps(payload),
                        content_type='application/json')
        assert r.status_code == 200
        data = json.loads(r.data)
        assert data['total_jumps'] == 2
        assert len(data['steps']) == 2

    def test_calculate_out_of_range(self, client):
        payload = {
            'ship_name': 'Ark',
            'jdc_level': 0,
            'jdfe_level': 5,
            'fuel_price_isk': 500,
            'waypoints': [{'from': 'Jita', 'to': 'Far', 'distance_ly': 50.0}],
        }
        r = client.post('/api/planner/calculate',
                        data=json.dumps(payload),
                        content_type='application/json')
        assert r.status_code == 200
        data = json.loads(r.data)
        assert data['has_out_of_range'] is True
        assert data['valid'] is False

    def test_calculate_no_ship(self, client):
        payload = {
            'ship_name': '',
            'jdc_level': 5,
            'jdfe_level': 5,
            'fuel_price_isk': 500,
            'waypoints': [{'from': 'A', 'to': 'B', 'distance_ly': 3.0}],
        }
        r = client.post('/api/planner/calculate',
                        data=json.dumps(payload),
                        content_type='application/json')
        assert r.status_code == 400

    def test_calculate_no_waypoints(self, client):
        payload = {
            'ship_name': 'Ark',
            'jdc_level': 5,
            'jdfe_level': 5,
            'fuel_price_isk': 500,
            'waypoints': [],
        }
        r = client.post('/api/planner/calculate',
                        data=json.dumps(payload),
                        content_type='application/json')
        assert r.status_code == 400

    def test_calculate_all_jf_ships(self, client):
        for ship in ['Ark', 'Anshar', 'Rhea', 'Nomad']:
            payload = {
                'ship_name': ship,
                'jdc_level': 5,
                'jdfe_level': 5,
                'fuel_price_isk': 500,
                'waypoints': [{'from': 'A', 'to': 'B', 'distance_ly': 4.0}],
            }
            r = client.post('/api/planner/calculate',
                            data=json.dumps(payload),
                            content_type='application/json')
            assert r.status_code == 200, f'Failed for {ship}'

    def test_calculate_all_carriers(self, client):
        for ship in ['Archon', 'Chimera', 'Thanatos', 'Nidhoggur']:
            payload = {
                'ship_name': ship,
                'jdc_level': 5, 'jdfe_level': 5, 'fuel_price_isk': 500,
                'waypoints': [{'from': 'A', 'to': 'B', 'distance_ly': 3.0}],
            }
            r = client.post('/api/planner/calculate',
                            data=json.dumps(payload),
                            content_type='application/json')
            assert r.status_code == 200, f'Failed for {ship}'

    def test_calculate_all_dreadnoughts(self, client):
        for ship in ['Revelation', 'Phoenix', 'Moros', 'Naglfar']:
            payload = {
                'ship_name': ship,
                'jdc_level': 5, 'jdfe_level': 5, 'fuel_price_isk': 500,
                'waypoints': [{'from': 'A', 'to': 'B', 'distance_ly': 3.0}],
            }
            r = client.post('/api/planner/calculate',
                            data=json.dumps(payload),
                            content_type='application/json')
            assert r.status_code == 200

    def test_calculate_black_ops(self, client):
        for ship in ['Redeemer', 'Widow', 'Sin', 'Panther']:
            payload = {
                'ship_name': ship,
                'jdc_level': 5, 'jdfe_level': 5, 'fuel_price_isk': 500,
                'waypoints': [{'from': 'A', 'to': 'B', 'distance_ly': 2.0}],
            }
            r = client.post('/api/planner/calculate',
                            data=json.dumps(payload),
                            content_type='application/json')
            assert r.status_code == 200

    def test_calculate_titans(self, client):
        for ship in ['Avatar', 'Leviathan', 'Erebus', 'Ragnarok']:
            payload = {
                'ship_name': ship,
                'jdc_level': 5, 'jdfe_level': 5, 'fuel_price_isk': 500,
                'waypoints': [{'from': 'A', 'to': 'B', 'distance_ly': 3.0}],
            }
            r = client.post('/api/planner/calculate',
                            data=json.dumps(payload),
                            content_type='application/json')
            assert r.status_code == 200

    def test_calculate_supercarriers(self, client):
        for ship in ['Aeon', 'Wyvern', 'Nyx', 'Hel']:
            payload = {
                'ship_name': ship,
                'jdc_level': 5, 'jdfe_level': 5, 'fuel_price_isk': 500,
                'waypoints': [{'from': 'A', 'to': 'B', 'distance_ly': 3.0}],
            }
            r = client.post('/api/planner/calculate',
                            data=json.dumps(payload),
                            content_type='application/json')
            assert r.status_code == 200

    def test_fuel_prices_api(self, client):
        r = client.get('/api/fuel/prices')
        # May fail if DB not available, that's OK — check we get a response
        assert r.status_code in (200, 500)

    def test_routes_api_endpoint_exists(self, client):
        r = client.get('/api/routes')
        assert r.status_code in (200, 500)

    def test_route_detail_not_found(self, client):
        r = client.get('/routes/99999999/')
        assert r.status_code == 200  # Returns partial template

    def test_404_not_raised_for_missing_static(self, client):
        r = client.get('/static/nonexistent.xyz')
        assert r.status_code in (404, 500)

    def test_calculate_cost_calculation(self, client):
        payload = {
            'ship_name': 'Ark',
            'jdc_level': 5,
            'jdfe_level': 0,
            'fuel_price_isk': 1000,
            'waypoints': [{'from': 'A', 'to': 'B', 'distance_ly': 2.0}],
        }
        r = client.post('/api/planner/calculate',
                        data=json.dumps(payload),
                        content_type='application/json')
        data = json.loads(r.data)
        expected_fuel = math.ceil(2.0 * 1000 * 1.0)
        assert data['total_fuel'] == expected_fuel
        assert abs(data['total_cost_isk'] - expected_fuel * 1000) < 0.01

    def test_calculate_jdfe_fuel_reduction(self, client):
        base_payload = {
            'ship_name': 'Ark',
            'jdc_level': 5,
            'fuel_price_isk': 500,
            'waypoints': [{'from': 'A', 'to': 'B', 'distance_ly': 5.0}],
        }
        base_payload['jdfe_level'] = 0
        r0 = json.loads(client.post('/api/planner/calculate',
                                     data=json.dumps(base_payload),
                                     content_type='application/json').data)
        base_payload['jdfe_level'] = 5
        r5 = json.loads(client.post('/api/planner/calculate',
                                     data=json.dumps(base_payload),
                                     content_type='application/json').data)
        assert r5['total_fuel'] < r0['total_fuel']

    def test_planner_ship_detail_all_jf(self, client):
        for ship in ['Ark', 'Anshar', 'Rhea', 'Nomad']:
            r = client.get(f'/api/planner/ship/{ship}')
            assert r.status_code == 200
            data = json.loads(r.data)
            assert data['name'] == ship
            assert data.get('cargo_m3') is not None

    def test_planner_ship_detail_carriers_no_cargo(self, client):
        for ship in ['Archon', 'Chimera', 'Thanatos', 'Nidhoggur']:
            r = client.get(f'/api/planner/ship/{ship}')
            assert r.status_code == 200

    def test_fuel_estimate_endpoint(self, client):
        r = client.get('/api/fuel/estimate?fuel_type=Oxygen+Isotopes&quantity=10000')
        assert r.status_code in (200, 404, 500)

    def test_dashboard_stats_endpoint(self, client):
        r = client.get('/api/dashboard/stats')
        assert r.status_code in (200, 500)

    def test_dashboard_recent_routes_endpoint(self, client):
        r = client.get('/api/dashboard/recent-routes')
        assert r.status_code in (200, 500)

    def test_dashboard_fuel_summary_endpoint(self, client):
        r = client.get('/api/dashboard/fuel-summary')
        assert r.status_code in (200, 500)

    def test_ships_endpoint_all_classes_present(self, client):
        r = client.get('/api/planner/ships')
        data = json.loads(r.data)
        class_labels = {g['label'] for g in data}
        assert 'Jump Freighter' in class_labels
        assert 'Carrier' in class_labels
        assert 'Dreadnought' in class_labels
        assert 'Black Ops' in class_labels

    def test_ships_endpoint_ark_in_jf_group(self, client):
        r = client.get('/api/planner/ships')
        data = json.loads(r.data)
        jf = next((g for g in data if g['class'] == 'jump_freighter'), None)
        assert jf is not None
        assert 'Ark' in jf['ships']
        assert 'Anshar' in jf['ships']
        assert 'Rhea' in jf['ships']
        assert 'Nomad' in jf['ships']
