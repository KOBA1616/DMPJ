"""入口局面で探索がループ証明書を作れているかの診断（docs/saga-loop-miss-20261113.md）。
  PYTHONPATH=. python tools/diag_loop_miss.py saga 1000
シードごとに、ターン内の勝ちの有無と、ループ検出器の成立数・verify の成否・失敗理由を出す。挙動は変えない（数えるだけ）。
"""
import sys,collections; sys.path.insert(0,'.')  # noqa
from dmsim.cards.defs import load_rules
from dmsim.eval import loop_entry as le, ruler_control as rc
from dmsim.engine import scenario
import dmsim.search.turn as T
r=load_rules(); ls=le.load(sys.argv[1] if len(sys.argv)>1 and not sys.argv[1].isdigit() else "saga"); deck=rc._deck(ls)
stat=collections.Counter()
ov=T.Detectors.observe
def obs(self,eng):
    c=ov(self,eng)
    if c: stat['cert']+=1; stat['burn' if T.is_burn_loop(c,0) else 'eng' if T.is_engine_loop(c,0) else 'other']+=1
    return c
T.Detectors.observe=obs
ovf=T.verify
def vf(eng,cert,times=1):
    c=ovf(eng,cert,times); stat['verify_ok' if c.verified>=1 else 'verify_ng']+=1
    if c.verified<1: stat['ng:'+(c.notes[-1][:40] if c.notes else '?')]+=1
    return c
T.verify=vf
for sd in ([int(x) for x in sys.argv[3].split(",")] if len(sys.argv) > 3 else range(13)):
    stat.clear()
    v=rc.vary(r,ls,sd); e=scenario.build(r,rc._entry_spec(v,deck,sd),first_player=0)
    leaf,st=T.TurnSearch(0,int(sys.argv[2])).run(e)
    print(sd,leaf.s.result and leaf.s.result['reason'],dict(stat),flush=True)
