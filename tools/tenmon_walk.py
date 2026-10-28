"""初期型天門ループの手順を、方針つきで一手ずつ回して確かめるスクリプト（探索ではなく手動方針）。python tools/tenmon_walk.py"""
import sys
from dmsim import load_rules, scenario
rules=load_rules()
HG,EM,MI,FA,MK="dm16-007","dm23bd7-022","dmx19-s06","dm31-025","dmx24-017"
OO,HC,TS,AL="dmd24-024","dmx11-082","dm23ex2-cho018","dmx12b-031"
F="T013"
W=["dm01-080"]*4+["dm06-085"]*4+["dm02-024"]*4                         # 水のマナ（4枚制限を守るため3種類）
spec={"p0":{"hand":[FA,FA,AL]+[F]*8,"bz":[EM,MI,OO],"mana":W,"shield":[HG]*4+[MK]*3,"deck":[TS,FA,FA,HC,MK]+[F]*8},
      "p1":{},"filler":F,"seed":1,"deck_size":14,"deck_exact":[True,False]}
assert not scenario.deck_limit_violations(rules,spec), scenario.deck_limit_violations(rules,spec)   # 同名カードは4枚まで
e=scenario.build(rules,spec)
dk=e.s.zones["deck"][0]
order=sorted(dk,key=lambda c:(e.s.cards[c].defn!=TS, e.s.cards[c].defn!=FA))   # TS, FA..., 先頭がTS
e.s.zones["deck"][0][:]=order
nm=lambda c: e.s.cards[c].defn
tgt=[MI]
last=None
yn=0
for step in range(200):
    d=e.advance()
    if d is None or e.s.result: break
    keys=[o["key"] for o in d["options"]]; k=d["kind"]
    pend=[(p["kind"][:3],p["defn"][-4:]) for p in e.s.pending]
    sh=len(e.zlist("shield",0))
    print(step,k,keys[:5],{a:b for a,b in d.items() if a not in ("options","kind","min","max")} if k=="yes_no" else "","sh",sh,"pend",len(pend))
    if k in("attack",): break
    if k=='main' and step>6: break
    ans=[0]
    if k=="charge": ans=[len(keys)-1]
    elif k=="main": ans=[next((i for i,x in enumerate(keys) if x.startswith("play:"+FA)),len(keys)-1)]
    elif k=="declare_strigger": ans=list(range(d["max"]))
    elif k=="order_pending":
        pri=lambda x:(0 if "cho018" in x else 1 if "dm31-025" in x else 2 if "dm23bd7" in x else 3)
        ans=[min(range(len(keys)),key=lambda i:pri(keys[i]))]; last=keys[ans[0]]
    elif k=="choose_cards" and any("bz:" in x for x in keys):
        t=tgt.pop(0) if tgt else (OO if last and "cho018" in last else EM)
        last=None
        ans=[next((i for i,x in enumerate(keys) if t in x),0)]
    elif k in("choose_cards","choose_shields") and keys and keys[0]=="shield":
        ans=[next((i for i,o in enumerate(d["options"]) if e.s.cards[o["cid"]].under),0)]
    elif k=="choose_cards" and any(AL in x for x in keys): ans=[next(i for i,x in enumerate(keys) if AL in x)]
    elif k=="choose_cards" and any("hand:"+F in x for x in keys): ans=[next(i for i,x in enumerate(keys) if "hand:"+F in x)]
    elif k=="choose_mode": ans=[next((i for i,x in enumerate(keys) if x=="mode:4"),0)]
    elif k=="yes_no":
        ans=([0] if any(e.s.cards[c].under for c in e.zlist("shield",0)) else [1]) if "ブレイク" in d["prompt"] else [0]
    e.answer(ans)
print("result",e.s.result,"shield",len(e.zlist("shield",0)))
