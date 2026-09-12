"""Reproducible perf_counter benchmark; no third-party benchmark dependency."""
import contextlib
import io
import json
import math
from pathlib import Path
import statistics
import sys
from time import perf_counter

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
import main
from tests.fixtures import integration_scenarios


def run(repeats=30):
    records=[]
    scenarios=integration_scenarios()
    for name in ['crowded_four','territory_split','royale_11','royale_19','long_snake','many_food','many_hazards']:
        for enabled in (False,True):
            times=[]
            with contextlib.redirect_stdout(io.StringIO()):
                main.move(scenarios[name],search_enabled=enabled)
                for _ in range(repeats):
                    started=perf_counter()
                    main.move(scenarios[name],search_enabled=enabled)
                    times.append((perf_counter()-started)*1000)
            ordered=sorted(times)
            records.append({'scenario':name,'search':enabled,'samples':repeats,
                            'mean_ms':round(statistics.mean(times),3),
                            'p95_ms':round(ordered[math.ceil(.95*len(times))-1],3),
                            'max_ms':round(max(times),3)})
    result={'python':sys.version,'benchmarks':records}
    path=ROOT/'reports'/'benchmark.json'
    path.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result,indent=2))


if __name__=='__main__':
    run()
