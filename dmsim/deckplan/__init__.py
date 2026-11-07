"""デッキ改善の枠（エンジン・カードデータには触れない）。記録形式 spec、変更の提案 change（登録式）、採否 evaluate、ループ loop。"""
from .spec import CONFIRMED, UNCONVERTED, UNRESOLVED, DeckProposal, Entry, check, load, save
from .change import Change, proposer
from .evaluate import AcceptRule, decide, harness_scorer
from .loop import improve
