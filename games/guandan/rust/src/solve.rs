//! Exact endgame solver: alpha-beta over the full (perfect-information) game tree of one deal, with a
//! transposition table. The value of a position is the levels gained by the root player's team (negative
//! when the other team wins the deal), with every player choosing the best move for their own team.

use std::collections::HashMap;

use crate::deal::{team, Deal};

pub struct Solver {
    me: usize, // the team whose levels are counted
    tt: HashMap<Vec<u8>, (i32, i32)>, // key -> (lower bound, upper bound)
    nodes: u64,
    limit: u64,
    pub aborted: bool,
}

const INF: i32 = 100;

fn key(d: &Deal) -> Vec<u8> {
    let mut k = Vec::with_capacity(48);
    for h in &d.hands {
        k.extend_from_slice(h);
        k.push(255);
    }
    k.push(d.to_act as u8);
    match &d.table {
        Some(m) => {
            k.push(m.combo.kind);
            k.extend_from_slice(&m.combo.value.to_le_bytes());
            k.push(m.combo.size);
            k.push(d.table_seat.unwrap() as u8);
        }
        None => k.push(254),
    }
    k.push(d.passes as u8);
    for &s in &d.finished {
        k.push(s as u8);
    }
    k
}

impl Solver {
    pub fn new(me: usize, limit: u64) -> Solver {
        Solver { me, tt: HashMap::new(), nodes: 0, limit, aborted: false }
    }

    /// A copy without the (unneeded) history, so cloning is cheap.
    fn lean(d: &Deal) -> Deal {
        let mut c = d.clone();
        c.history.clear();
        c.played = Default::default();
        c
    }

    fn search(&mut self, d: &mut Deal, mut alpha: i32, mut beta: i32) -> i32 {
        if d.done {
            let (win, up) = d.result();
            return if win == self.me { up } else { -up };
        }
        self.nodes += 1;
        if self.nodes > self.limit {
            self.aborted = true;
            return 0;
        }
        let k = key(d);
        if let Some(&(lo, hi)) = self.tt.get(&k) {
            if lo >= beta {
                return lo;
            }
            if hi <= alpha {
                return hi;
            }
            if lo == hi {
                return lo;
            }
            alpha = alpha.max(lo);
            beta = beta.min(hi);
        }
        let (a0, b0) = (alpha, beta);
        let maximizing = team(d.to_act as usize) == self.me;
        let mut moves = d.legal().clone();
        // try big plays first, passing last: shedding cards early is usually right and prunes well
        moves.sort_by_key(|m| if m.is_pass() { 1000 } else { -(m.cards.len() as i32) });
        let mut best = if maximizing { -INF } else { INF };
        for mv in moves {
            let mut c = d.clone();
            c.play(mv).expect("legal move");
            let v = self.search(&mut c, alpha, beta);
            if self.aborted {
                return 0;
            }
            if maximizing {
                best = best.max(v);
                alpha = alpha.max(v);
            } else {
                best = best.min(v);
                beta = beta.min(v);
            }
            if alpha >= beta {
                break;
            }
        }
        let entry = self.tt.entry(k).or_insert((-INF, INF));
        if best <= a0 {
            entry.1 = entry.1.min(best);
        } else if best >= b0 {
            entry.0 = entry.0.max(best);
        } else {
            *entry = (best, best);
        }
        best
    }

    /// Exact value of every legal move of the player to act, or None if the node budget ran out.
    pub fn root_values(deal: &Deal, limit: u64) -> Option<Vec<i32>> {
        let mut root = Solver::lean(deal);
        let me = team(root.to_act as usize);
        let mut s = Solver::new(me, limit);
        let moves = root.legal().clone();
        let mut out = Vec::with_capacity(moves.len());
        for mv in moves {
            let mut c = root.clone();
            c.play(mv).expect("legal move");
            let v = s.search(&mut c, -INF, INF);
            if s.aborted {
                return None;
            }
            out.push(v);
        }
        Some(out)
    }
}
