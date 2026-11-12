//! Hand decomposition: the fewest sets (combos) a hand can be split into, i.e. how many leads it takes to go
//! out if nobody ever beats you. Used as a feature: the fewer sets, the closer the hand is to done, and a move
//! is good for the plan when it removes a whole set without breaking others.
//!
//! Counts per natural rank plus the jokers and the two wild cards; sets are single, pair, triple, bomb, full
//! house, straight, tube (3 pairs) and plate (2 triples), with wilds filling gaps. Exact DFS over the lowest
//! remaining rank, memoised; full-house partners are limited to the lowest few candidates to keep it fast.

use std::collections::HashMap;

use crate::combos::{ctype, wild_type, BJ, SJ};

#[derive(Clone, Copy)]
pub struct St {
    pub nr: [u8; 13],
    pub sj: u8,
    pub bj: u8,
    pub w: u8,
}

impl St {
    pub fn from_cards(cards: &[u8], level: u8) -> St {
        let wt = wild_type(level);
        let mut s = St { nr: [0; 13], sj: 0, bj: 0, w: 0 };
        for &c in cards {
            let t = ctype(c);
            if t == wt {
                s.w += 1;
            } else if t == SJ {
                s.sj += 1;
            } else if t == BJ {
                s.bj += 1;
            } else {
                s.nr[(t % 13) as usize] += 1;
            }
        }
        s
    }

    pub fn minus(&self, cards: &[u8], level: u8) -> St {
        let wt = wild_type(level);
        let mut s = *self;
        for &c in cards {
            let t = ctype(c);
            if t == wt {
                s.w = s.w.saturating_sub(1);
            } else if t == SJ {
                s.sj = s.sj.saturating_sub(1);
            } else if t == BJ {
                s.bj = s.bj.saturating_sub(1);
            } else {
                let r = (t % 13) as usize;
                s.nr[r] = s.nr[r].saturating_sub(1);
            }
        }
        s
    }

    fn key(&self) -> u64 {
        let mut k = 0u64;
        for &c in &self.nr {
            k = (k << 4) | c as u64;
        }
        (((k << 2) | self.sj as u64) << 2 | self.bj as u64) << 2 | self.w as u64
    }
}

#[derive(Default)]
pub struct Planner {
    memo: HashMap<u64, u8>,
}

impl Planner {
    pub fn new() -> Planner {
        Planner { memo: HashMap::new() }
    }

    /// Take the (rank, count) demands from the state, filling shortfalls with wilds; the cost is one set.
    fn step(&mut self, st: &St, demand: &[(usize, u8)]) -> Option<u8> {
        let mut s = *st;
        let mut deficit = 0u8;
        for &(r, need) in demand {
            let have = s.nr[r].min(need);
            s.nr[r] -= have;
            deficit += need - have;
        }
        if deficit > s.w {
            return None;
        }
        s.w -= deficit;
        Some(1 + self.min_sets(&s))
    }

    pub fn min_sets(&mut self, st: &St) -> u8 {
        let k = st.key();
        if let Some(&v) = self.memo.get(&k) {
            return v;
        }
        let r = match (0..13).find(|&i| st.nr[i] > 0) {
            None => {
                let jokers = if st.sj == 2 && st.bj == 2 { 1 } else { (st.sj > 0) as u8 + (st.bj > 0) as u8 };
                let v = jokers + (st.w + 1) / 2;
                self.memo.insert(k, v);
                return v;
            }
            Some(r) => r,
        };
        let c = st.nr[r];
        let mut best = u8::MAX;
        let mut consider = |v: Option<u8>| {
            if let Some(v) = v {
                best = best.min(v);
            }
        };
        // sets inside one rank
        for n in 1..=3u8 {
            consider(self.step(st, &[(r, n)]));
        }
        consider(self.step(st, &[(r, 4)]));
        if c > 4 {
            consider(self.step(st, &[(r, c)]));
        }
        // full houses with the lowest few partner ranks
        let mut pairs = 0;
        let mut triples = 0;
        for s in r + 1..13 {
            if st.nr[s] >= 2 && pairs < 2 {
                pairs += 1;
                consider(self.step(st, &[(r, 3), (s, 2)]));
            }
            if st.nr[s] >= 3 && triples < 2 {
                triples += 1;
                consider(self.step(st, &[(r, 2), (s, 3)]));
            }
        }
        // sequences starting at the lowest rank (the ace also counts low)
        if r + 4 <= 12 {
            consider(self.step(st, &[(r, 1), (r + 1, 1), (r + 2, 1), (r + 3, 1), (r + 4, 1)]));
        }
        if r + 2 <= 12 {
            consider(self.step(st, &[(r, 2), (r + 1, 2), (r + 2, 2)]));
        }
        if r + 1 <= 12 {
            consider(self.step(st, &[(r, 3), (r + 1, 3)]));
        }
        if r == 0 {
            consider(self.step(st, &[(12, 1), (0, 1), (1, 1), (2, 1), (3, 1)]));
            consider(self.step(st, &[(12, 2), (0, 2), (1, 2)]));
            consider(self.step(st, &[(12, 3), (0, 3)]));
        }
        self.memo.insert(k, best);
        best
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    fn sets(counts: &[(usize, u8)], sj: u8, bj: u8, w: u8) -> u8 {
        let mut st = St { nr: [0; 13], sj, bj, w };
        for &(r, n) in counts {
            st.nr[r] = n;
        }
        Planner::new().min_sets(&st)
    }

    #[test]
    fn known_hands() {
        assert_eq!(sets(&[], 0, 0, 0), 0);
        assert_eq!(sets(&[(3, 3), (5, 2), (8, 4)], 0, 1, 0), 3);       // full house + bomb + big joker
        assert_eq!(sets(&[(0, 1), (1, 1), (2, 1), (3, 1), (4, 1)], 0, 0, 0), 1); // straight
        assert_eq!(sets(&[(0, 2), (1, 2), (2, 2)], 0, 0, 0), 1);       // tube
        assert_eq!(sets(&[(4, 3), (5, 3)], 0, 0, 0), 1);               // plate
        assert_eq!(sets(&[(0, 1), (3, 1), (6, 1), (9, 1)], 0, 0, 0), 4); // four loose singles
        assert_eq!(sets(&[(3, 1)], 0, 0, 1), 1);                        // single + wild = a pair
        assert_eq!(sets(&[(3, 3)], 0, 0, 1), 1);                        // triple + wild = a bomb
        assert_eq!(sets(&[], 2, 2, 0), 1);                              // joker bomb
    }
}
