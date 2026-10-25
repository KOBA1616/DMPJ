"""追加カード（タイフーン2種・イザナギ・ブルース・サガ）を配置から探索させ、ループと勝ちが出るか見る。
実行: PYTHONPATH=. python tools/loopcheck_cards.py"""
import sys; sys.path.insert(0,'tests')
from dmsim.defs import load_rules
from dmsim import scenario as sc
from dmsim.solitaire import play_game
r=load_rules()
IZ="dm22ex1-025"; ET="dm26ex2-071"; LT="dmpromoy22-p51"; BR="dmbd17-009"; SAGA="dm22ex2-021"
def run(name, p0, deck_left=30, budget=3000, turns=1):
    spec={"p0":p0,"p1":{},"deck_size":40,"deck_left":[deck_left,40],"seed":1}
    eng=sc.build(r,spec)
    res,e=play_game(r,None,None,1,max_turn=turns,start=eng,lock_rounds=0,budget=budget)
    print(name, res.kind, res.kill_turn, res.error, [ (l["kind"],l["delta"],l["stocked"]) for l in res.loops][:3], res.nodes, round(res.seconds,1), "deck",len(e.s.zones["deck"][0]),"gy",len(e.s.zones["graveyard"][0]))
M=["dm06-085"]*5+["dm01-027"]*3
run("typhoons+izanagi", {"hand":[IZ,ET,LT,BR],"mana":M,"graveyard":["T001"]*8})
run("saga+typhoon", {"hand":[SAGA,ET,LT,BR,IZ],"mana":M,"graveyard":[SAGA]+["T001"]*10})
run("bruce gy13", {"hand":[BR,ET,LT],"mana":M,"graveyard":["T001"]*13,"bz":[LT]})
