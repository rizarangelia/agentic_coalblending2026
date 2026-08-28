import json, pathlib, sys
sys.path.insert(0, str(pathlib.Path(__file__).parent.parent))
from agents import ingestion, constraint, optimizer

ROOT = pathlib.Path(__file__).parent.parent
M = json.loads((ROOT/'config/constraint_manifest.json').read_text())
EXP = json.loads((ROOT/'fixtures/expected_solution_simulasi.json').read_text())

def load_fixtures(mut=None):
    fx = {k: [(ROOT/f'fixtures/{k}_simulasi.csv').read_bytes(), f'{k}.csv']
          for k in ('opening_stock','coal_getting','demand_deal','plan_kapasitas')}
    if mut: fx = mut(fx)
    return {k:(v[0],v[1]) for k,v in fx.items()}

def test_baseline():
    data, a1 = ingestion.ingest(load_fixtures(), M)
    assert data and data['status']=='VALID', a1
    C, a2 = constraint.build(M, data)
    sol, a3 = optimizer.solve(C)
    assert sol, a3
    assert abs(sol['revenue'] - EXP['objective_revenue']) < 1, sol['revenue']
    assert abs(sol['total_ship'] - EXP['total_shipment']) < 1
    for s,v in EXP['closing_stock'].items():
        assert abs(sol['closing'][s]-v) < 1, (s, sol['closing'][s])
    print('PASS baseline: revenue', round(sol['revenue'],2), '| alerts:', len(a1+a2+a3))
    for a in a1+a2+a3: print('  ', a[0], a[1], '-', a[2][:95])

def test_reject_negative():
    def mut(fx):
        fx['opening_stock'][0] = fx['opening_stock'][0].replace(b'200000', b'-200000'); return fx
    data, a1 = ingestion.ingest(load_fixtures(mut), M)
    assert data is None and any('negatif' in a[2] for a in a1)
    print('PASS reject data negatif')

def test_infeasible_presolve():
    def mut(fx):
        fx['plan_kapasitas'][0] = b"jetty,kapasitas_mt\nLati,300000\nBinungan,400000\nSambarata,200000\nGurimbang,200000\nBMO3,100000\n"
        return fx
    data, a1 = ingestion.ingest(load_fixtures(mut), M)
    C, a2 = constraint.build(M, data)
    assert any(s=='CRITICAL' for s,_,_ in a2), 'pre-solve harus mendeteksi deal>kapasitas'
    print('PASS pre-solve deteksi infeasible:', a2[0][2][:85])

def test_solver_diagnoser():
    M2 = json.loads(json.dumps(M)); M2['closing_stock_band_simulasi']['Sambarata']={'min':550000,'max':600000}
    data,_ = ingestion.ingest(load_fixtures(), M2)
    C,_ = constraint.build(M2, data)
    sol, a3 = optimizer.solve(C)
    assert sol is None and any('relaksasi minimum' in a[2] for a in a3), a3
    print('PASS solver diagnoser:')
    for a in a3[:3]: print('  ', a[2][:95])

test_baseline(); test_reject_negative(); test_infeasible_presolve(); test_solver_diagnoser()
