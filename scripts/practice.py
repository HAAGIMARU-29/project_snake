"""Repeat CLI games against the preserved baseline (or self-play).

Run with the project venv. Starts temporary servers on 8100/8101 and stops only
its own processes. Refuses to reuse existing listeners. Detailed replays/logs
stay in the chosen output directory; summary.json is suitable for review.
"""
import argparse
import json
import os
import re
from pathlib import Path
import socket
import subprocess
import sys
import tempfile
import time
import urllib.request

ROOT=Path(__file__).resolve().parents[1]
BASELINE='25b0cd6'


def run():
    parser=argparse.ArgumentParser()
    parser.add_argument('--output',default='reports/practice')
    parser.add_argument('--seeds',type=int,nargs='+',default=[101,202,303])
    parser.add_argument('--self-play',action='store_true')
    args=parser.parse_args()
    output=Path(args.output).resolve()
    output.mkdir(parents=True,exist_ok=True)
    for port in (8100,8101):
        with socket.socket() as probe:
            probe.setsockopt(socket.SOL_SOCKET,socket.SO_REUSEADDR,1)
            probe.bind(('127.0.0.1',port))
    processes=[]
    handles=[]
    records=[]
    try:
        with tempfile.TemporaryDirectory(prefix='snake-practice-') as temp:
            baseline=Path(temp)/'baseline.py'
            baseline.write_text(subprocess.check_output(['git','show',f'{BASELINE}:main.py'],cwd=ROOT,text=True))
            for name,port,entry in [('bot',8100,ROOT/'main.py'),('opponent',8101,ROOT/'main.py' if args.self_play else baseline)]:
                log=(output/f'{name}.log').open('w')
                handles.append(log)
                env=dict(os.environ,PORT=str(port),PYTHONPATH=str(ROOT),PYTHONUNBUFFERED='1',BATTLESNAKE_LOG='1')
                process=subprocess.Popen([sys.executable,str(entry)],cwd=ROOT,env=env,stdout=log,stderr=subprocess.STDOUT)
                processes.append(process)
                for _ in range(100):
                    if process.poll() is not None:
                        raise RuntimeError(f'{name} server failed; see {output/name}.log')
                    try:
                        with urllib.request.urlopen(f'http://127.0.0.1:{port}',timeout=.2) as response:
                            assert response.status==200
                        break
                    except OSError:
                        time.sleep(.05)
                else:
                    raise RuntimeError('server startup deadline exceeded')
            for mode,size in [('standard',11),('royale',11),('royale',19)]:
                for seed in args.seeds:
                    label=f'{mode}-{size}-{seed}'
                    replay=output/f'{label}.jsonl'
                    command=['battlesnake','play','-W',str(size),'-H',str(size),'-g',mode,'--seed',str(seed),'--timeout','500','-v','--output',str(replay),'--name','TournamentBot','--url','http://localhost:8100']
                    for i in range(3):
                        command.extend(['--name',f'Opponent{i+1}','--url','http://localhost:8101'])
                    started=time.perf_counter()
                    completed=subprocess.run(command,cwd=ROOT,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,timeout=120)
                    (output/f'{label}.log').write_text(completed.stdout)
                    if completed.returncode:
                        raise RuntimeError(f'CLI failed: {label}; see match log')
                    frames=[json.loads(line) for line in replay.read_text().splitlines()]
                    deaths={}
                    for name,cause,turn in re.findall(r'(TournamentBot|Opponent[123]) [^:]+: Health: -?\d+, Eliminated: ([\w-]+), Turn: (\d+)',completed.stdout):
                        deaths[name]={'cause':cause,'turn':int(turn)}
                    record={'deaths':deaths,'mode':mode,'size':size,'seed':seed,'seconds':round(time.perf_counter()-started,2),'result':frames[-1]}
                    records.append(record)
                    print(json.dumps(record),flush=True)
    finally:
        for process in processes:
            process.terminate()
        for process in processes:
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait()
        for handle in handles:
            handle.close()
        (output/'summary.json').write_text(json.dumps({'opponent':'self' if args.self_play else BASELINE,'matches':records},indent=2)+'\n')


if __name__=='__main__':
    run()
