//! Cards, combos and legal-move generation: a line-for-line port of guandan/cards.py and
//! guandan/combos.py (`legal_moves`), including which concrete cards get picked and the
//! order of the result, so either backend produces identical move lists.

use std::collections::HashSet;

pub const SJ: u8 = 52;
pub const BJ: u8 = 53;
pub const N_TYPES: usize = 54;
pub const N_CARDS: usize = 108;
pub const LEVEL_VALUE: i32 = 13;
pub const SJ_VALUE: i32 = 14;
pub const BJ_VALUE: i32 = 15;

pub const PASS: u8 = 0;
pub const SINGLE: u8 = 1;
pub const PAIR: u8 = 2;
pub const TRIPLE: u8 = 3;
pub const FULL_HOUSE: u8 = 4;
pub const STRAIGHT: u8 = 5;
pub const TUBE: u8 = 6;
pub const PLATE: u8 = 7;
pub const BOMB: u8 = 8;
pub const STRAIGHT_FLUSH: u8 = 9;
pub const JOKER_BOMB: u8 = 10;
pub const N_KINDS: usize = 11;

/// Sequence position i -> rank; the ace appears at both ends.
const SEQ: [usize; 14] = [12, 0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12];
/// (kind, length, copies per rank), in the order the Python dict iterates.
const SEQ_SPEC: [(u8, usize, i32); 3] = [(STRAIGHT, 5, 1), (TUBE, 3, 2), (PLATE, 2, 3)];

#[inline]
pub fn ctype(c: u8) -> u8 {
    c % N_TYPES as u8
}

#[inline]
pub fn wild_type(level: u8) -> u8 {
    13 + level
}

#[inline]
pub fn value(t: u8, level: u8) -> i32 {
    if t == SJ {
        SJ_VALUE
    } else if t == BJ {
        BJ_VALUE
    } else {
        let r = t % 13;
        if r == level { LEVEL_VALUE } else { r as i32 }
    }
}

#[inline]
pub fn sort_key(c: u8, level: u8) -> (i32, u8) {
    let t = ctype(c);
    (value(t, level), t)
}

#[derive(Clone, Copy, PartialEq, Eq, Hash, Debug)]
pub struct Combo {
    pub kind: u8,
    pub value: i32,
    pub size: u8,
}

impl Combo {
    pub const PASS: Combo = Combo { kind: PASS, value: 0, size: 0 };

    #[inline]
    pub fn is_bomb(&self) -> bool {
        self.kind >= BOMB
    }

    pub fn power(&self) -> (i32, i32) {
        match self.kind {
            JOKER_BOMB => (100, 0),
            STRAIGHT_FLUSH => (11, self.value),
            _ => (2 * self.size as i32, self.value),
        }
    }

    pub fn beats(&self, other: Option<&Combo>) -> bool {
        if self.kind == PASS {
            return false;
        }
        let Some(o) = other else { return true };
        if self.is_bomb() {
            !o.is_bomb() || self.power() > o.power()
        } else {
            !o.is_bomb() && self.kind == o.kind && self.value > o.value
        }
    }
}

#[derive(Clone, Debug)]
pub struct Move {
    pub combo: Combo,
    pub cards: Vec<u8>,
}

impl Move {
    pub fn pass() -> Move {
        Move { combo: Combo::PASS, cards: Vec::new() }
    }
    pub fn is_pass(&self) -> bool {
        self.combo.kind == PASS
    }
}

#[inline]
fn same_rank_value(r: usize, level: u8) -> i32 {
    if r == level as usize { LEVEL_VALUE } else { r as i32 }
}

struct Picker {
    w: u8,
    by_type: Vec<Vec<u8>>, // card ids per type, in hand order
    nr: [i32; 13],
    suited: [[i32; 13]; 4],
    wild: i32,
    sj: i32,
    bj: i32,
    nat: Vec<Vec<u8>>, // naturals per rank, least-useful suits first
}

impl Picker {
    fn new(hand: &[u8], level: u8) -> Picker {
        let w = wild_type(level);
        let mut by_type = vec![Vec::new(); N_TYPES];
        let (mut nr, mut suited) = ([0i32; 13], [[0i32; 13]; 4]);
        let (mut wild, mut sj, mut bj) = (0, 0, 0);
        for &c in hand {
            let t = ctype(c);
            by_type[t as usize].push(c);
            if t == w {
                wild += 1;
            } else if t == SJ {
                sj += 1;
            } else if t == BJ {
                bj += 1;
            } else {
                nr[(t % 13) as usize] += 1;
                suited[(t / 13) as usize][(t % 13) as usize] += 1;
            }
        }
        let mut has = [[0i32; 13]; 4];
        for s in 0..4 {
            for r in 0..13 {
                has[s][r] = (suited[s][r] > 0) as i32;
            }
        }
        let mut nat = Vec::with_capacity(13);
        for r in 0..13usize {
            let score = |s: usize| -> (i32, usize) {
                let lo = r.saturating_sub(4);
                let hi = (r + 4).min(12);
                let sum: i32 = has[s][lo..=hi].iter().sum();
                (sum - has[s][r], s)
            };
            let mut suits: Vec<usize> = (0..4).collect();
            suits.sort_by_key(|&s| score(s));
            let mut cards = Vec::new();
            for s in suits {
                let t = s * 13 + r;
                if t as u8 != w {
                    cards.extend_from_slice(&by_type[t]);
                }
            }
            nat.push(cards);
        }
        Picker { w, by_type, nr, suited, wild, sj, bj, nat }
    }

    fn wilds(&self) -> &[u8] {
        &self.by_type[self.w as usize]
    }

    fn take(&self, demand: &[(usize, i32)], suit: Option<usize>) -> Option<Vec<u8>> {
        let mut cards: Vec<u8> = Vec::with_capacity(8);
        let mut need_wild = 0usize;
        for &(r, k) in demand {
            let k = k as usize;
            let before = cards.len();
            match suit {
                None => cards.extend(self.nat[r].iter().take(k)),
                Some(s) => {
                    let t = s * 13 + r;
                    if t as u8 != self.w {
                        cards.extend(self.by_type[t].iter().take(k));
                    }
                }
            }
            need_wild += k - (cards.len() - before);
        }
        let wilds = self.wilds();
        if need_wild > wilds.len() {
            return None;
        }
        cards.extend_from_slice(&wilds[..need_wild]);
        Some(cards)
    }
}

struct Collector<'a> {
    table: Option<&'a Combo>,
    seen: HashSet<(Combo, Vec<u8>)>,
    moves: Vec<Move>,
}

impl<'a> Collector<'a> {
    fn add(&mut self, p: &Picker, combo: Combo, demand: &[(usize, i32)], suit: Option<usize>, extra: &[u8]) {
        if !combo.beats(self.table) {
            return;
        }
        let cards = if demand.is_empty() { Some(Vec::new()) } else { p.take(demand, suit) };
        if let Some(mut cards) = cards {
            cards.extend_from_slice(extra);
            let mut key: Vec<u8> = cards.iter().map(|&c| ctype(c)).collect();
            key.sort_unstable();
            if self.seen.insert((combo, key)) {
                self.moves.push(Move { combo, cards });
            }
        }
    }
}

/// All moves from `hand` that may be played over `table` (None = leading); PASS excluded.
pub fn legal_moves(hand: &[u8], level: u8, table: Option<&Combo>) -> Vec<Move> {
    let p = Picker::new(hand, level);
    let mut col = Collector { table, seen: HashSet::new(), moves: Vec::new() };
    let lv = level as usize;
    let avail = |r: usize| p.nr[r] > 0 || (r == lv && p.wild > 0);

    for r in 0..13usize {
        if !avail(r) {
            continue;
        }
        let v = same_rank_value(r, level);
        for n in 1..=(p.nr[r] + p.wild) {
            let kind = match n { 1 => SINGLE, 2 => PAIR, 3 => TRIPLE, _ => BOMB };
            col.add(&p, Combo { kind, value: v, size: n as u8 }, &[(r, n)], None, &[]);
        }
    }
    for (jt, cnt, v) in [(SJ, p.sj, SJ_VALUE), (BJ, p.bj, BJ_VALUE)] {
        let cards = &p.by_type[jt as usize];
        if cnt > 0 {
            col.add(&p, Combo { kind: SINGLE, value: v, size: 1 }, &[], None, &cards[..1]);
        }
        if cnt == 2 {
            col.add(&p, Combo { kind: PAIR, value: v, size: 2 }, &[], None, cards);
        }
    }
    if p.sj == 2 && p.bj == 2 {
        let mut extra = p.by_type[SJ as usize].clone();
        extra.extend_from_slice(&p.by_type[BJ as usize]);
        col.add(&p, Combo { kind: JOKER_BOMB, value: 0, size: 4 }, &[], None, &extra);
    }

    // Full houses: any triple with any pair (including a joker pair).
    let triples: Vec<usize> = (0..13).filter(|&r| avail(r) && p.nr[r] + p.wild >= 3).collect();
    for &a in &triples {
        let va = same_rank_value(a, level);
        let fh = Combo { kind: FULL_HOUSE, value: va, size: 5 };
        for b in 0..13usize {
            if b != a && avail(b) && p.nr[b] + p.wild >= 2 {
                col.add(&p, fh, &[(a, 3), (b, 2)], None, &[]);
            }
        }
        for (jt, cnt) in [(SJ, p.sj), (BJ, p.bj)] {
            if cnt == 2 {
                col.add(&p, fh, &[(a, 3)], None, &p.by_type[jt as usize]);
            }
        }
    }

    for (kind, length, copies) in SEQ_SPEC {
        for i in 0..=(SEQ.len() - length) {
            let demand: Vec<(usize, i32)> = (0..length).map(|k| (SEQ[i + k], copies)).collect();
            col.add(&p, Combo { kind, value: i as i32, size: (length as i32 * copies) as u8 }, &demand, None, &[]);
        }
    }
    for s in 0..4usize {
        for i in 0..=(SEQ.len() - 5) {
            let demand: Vec<(usize, i32)> = (0..5).map(|k| (SEQ[i + k], 1)).collect();
            let have = demand.iter().filter(|&&(r, _)| p.suited[s][r] > 0).count() as i32;
            if have + p.wild >= 5 {
                col.add(&p, Combo { kind: STRAIGHT_FLUSH, value: i as i32, size: 5 }, &demand, Some(s), &[]);
            }
        }
    }
    let mut out = col.moves;
    out.sort_by_key(|m| {
        let c = &m.combo;
        (c.is_bomb(), c.kind, if c.is_bomb() { c.power() } else { (0, c.value) })
    });
    out
}
