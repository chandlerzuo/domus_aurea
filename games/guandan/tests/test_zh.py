from guandan.cards import BJ, SJ, parse
from guandan.combos import PASS, Combo, Kind, Move
from guandan.server import zh


def test_cards_and_moves_in_chinese():
    assert zh.card_zh(parse("Th")[0]) == "♥10" and zh.card_zh(SJ) == "小王" and zh.card_zh(BJ) == "大王"
    assert zh.move_zh(PASS) == "不出"
    assert zh.move_zh(Move(Combo(Kind.PAIR, 1, 2), tuple(parse("3s 3d")))) == "对子 ♠3 ♦3"
    assert zh.move_zh(Move(Combo(Kind.BOMB, 1, 5), tuple(parse("3s 3d 3c 3h 3s")))).startswith("5张炸弹")
    assert all(k in zh.KINDS for k in Kind)


def test_errors_translated_with_fallback():
    assert zh.error_zh("not your turn") == "还没轮到你"
    assert zh.error_zh("something new") == "something new"
