"""Chinese text for the web app: seat names, card and combo names, log lines, error messages.

The rules engine and the training code stay in English; only text that the
browser shows goes through here.
"""
from __future__ import annotations

from ..cards import BJ, SJ, ctype
from ..combos import Kind, Move

SEATS = ["南", "东", "北", "西"]
TEAMS = ["南北", "东西"]
PLACES = ["头游", "二游", "三游", "末游"]
RANKS_ZH = ["2", "3", "4", "5", "6", "7", "8", "9", "10", "J", "Q", "K", "A"]
SUITS_ZH = "♠♥♣♦"
AGENTS = {"ppo": "PPO", "dmc": "DMC", "heuristic": "规则", "random": "随机"}
KINDS = {
    Kind.PASS: "不出", Kind.SINGLE: "单张", Kind.PAIR: "对子", Kind.TRIPLE: "三张",
    Kind.FULL_HOUSE: "三带二", Kind.STRAIGHT: "顺子", Kind.TUBE: "三连对", Kind.PLATE: "钢板",
    Kind.BOMB: "炸弹", Kind.STRAIGHT_FLUSH: "同花顺", Kind.JOKER_BOMB: "四王炸",
}


def rank_zh(rank: int) -> str:
    return RANKS_ZH[rank]


def card_zh(card: int) -> str:
    t = ctype(card)
    if t == SJ:
        return "小王"
    if t == BJ:
        return "大王"
    return SUITS_ZH[t // 13] + RANKS_ZH[t % 13]


def kind_zh(move: Move) -> str:
    k = move.combo.kind
    return f"{move.combo.size}张炸弹" if k == Kind.BOMB else KINDS[k]


def move_zh(move: Move) -> str:
    if move.is_pass:
        return "不出"
    return f"{kind_zh(move)} {' '.join(card_zh(c) for c in move.cards)}"


def ai_name(seat: int, kind: str) -> str:
    return f"{SEATS[seat]}·AI（{AGENTS.get(kind, kind)}）"


# Error messages raised by the engine and the table logic, as shown to players.
ERRORS = {
    "not your turn": "还没轮到你",
    "the leader must play": "首家必须出牌",
    "those cards are not in your hand": "这些牌不在你手里",
    "not a valid combination": "不是有效的牌型",
    "does not beat the table": "压不过桌上的牌",
    "no return owed": "你不需要还贡",
    "return a card of rank 10 or lower": "还贡请选一张 10 或以下的牌",
    "deal still in progress": "本局还没结束",
    "deal is over": "本局已结束",
    "the match has already started": "对局已经开始",
    "that seat is taken": "这个座位已经有人了",
    "only the host can change seats before the start": "只有桌主能在开局前调整座位",
    "that seat has a person in it": "这个座位上有玩家",
    "only the host can start the match": "只有桌主能开始对局",
    "fill every seat (with people or AI) first": "请先坐满所有座位（玩家或 AI）",
    "unknown agent": "未知的 AI 类型",
    "you are not seated at this table": "你不在这张桌子上",
    "the match has not started": "对局还没开始",
    "no such table": "没有这张桌子",
    "no such deal": "没有这一局",
    "seat must be 0-3": "座位号必须是 0–3",
    "not found": "找不到",
    "unknown command": "未知操作",
    "JSON required": "请求格式错误",
    "request too large": "请求太大",
    "bad host": "地址不被允许",
    "reviews need a trained policy (runs/ppo/model.pt)": "复盘需要训练好的模型（runs/ppo/model.pt）",
}


def error_zh(message: str) -> str:
    return ERRORS.get(message, message)
