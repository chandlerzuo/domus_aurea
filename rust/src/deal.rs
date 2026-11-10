//! One deal of Guandan: a port of guandan/game.py `Deal` (same rules, same state).

use crate::combos::{legal_moves, sort_key, Move};

const UPGRADE: [i32; 4] = [0, 3, 2, 1]; // partner's finishing index -> levels gained

#[inline]
pub fn team(seat: usize) -> usize {
    seat % 2
}
#[inline]
pub fn partner(seat: usize) -> usize {
    (seat + 2) % 4
}

#[derive(Clone)]
pub struct Deal {
    pub hands: [Vec<u8>; 4],
    pub level: u8,
    pub team_levels: [u8; 2],
    pub level_team: Option<u8>,
    pub to_act: i32, // -1 once the deal is over
    pub table: Option<Move>,
    pub table_seat: Option<usize>,
    pub passes: usize,
    pub finished: Vec<usize>,
    pub history: Vec<(usize, Move)>,
    pub played: [Vec<u8>; 4],
    pub done: bool,
    legal_cache: Option<Vec<Move>>,
}

impl Deal {
    pub fn new(hands: Vec<Vec<u8>>, level: u8, leader: usize, team_levels: [u8; 2], level_team: Option<u8>) -> Deal {
        let mut hs: [Vec<u8>; 4] = Default::default();
        for (i, mut h) in hands.into_iter().enumerate().take(4) {
            h.sort_by_key(|&c| sort_key(c, level)); // stable, like Python's sorted()
            hs[i] = h;
        }
        Deal {
            hands: hs, level, team_levels, level_team, to_act: leader as i32, table: None, table_seat: None,
            passes: 0, finished: Vec::new(), history: Vec::new(), played: Default::default(), done: false,
            legal_cache: None,
        }
    }

    /// A deal in the middle of play (state given explicitly; hands are used as given).
    #[allow(clippy::too_many_arguments)]
    pub fn from_state(hands: Vec<Vec<u8>>, level: u8, to_act: usize, team_levels: [u8; 2], level_team: Option<u8>,
                      table: Option<Move>, table_seat: Option<usize>, passes: usize, finished: Vec<usize>,
                      history: Vec<(usize, Move)>, played: Vec<Vec<u8>>) -> Deal {
        let mut d = Deal::new(hands, level, to_act, team_levels, level_team);
        d.table = table;
        d.table_seat = table_seat;
        d.passes = passes;
        d.finished = finished;
        d.history = history;
        for (i, p) in played.into_iter().enumerate().take(4) {
            d.played[i] = p;
        }
        d
    }

    pub fn reset_cache(&mut self) {
        self.legal_cache = None;
    }

    #[inline]
    pub fn leading(&self) -> bool {
        self.table.is_none()
    }

    #[inline]
    pub fn active(&self, seat: usize) -> bool {
        !self.finished.contains(&seat)
    }

    /// Legal moves for the player to act (PASS first when following).
    pub fn legal(&mut self) -> &Vec<Move> {
        if self.legal_cache.is_none() {
            let seat = self.to_act as usize;
            let tc = self.table.as_ref().map(|m| m.combo);
            let mut moves = legal_moves(&self.hands[seat], self.level, tc.as_ref());
            if !self.leading() {
                moves.insert(0, Move::pass());
            }
            self.legal_cache = Some(moves);
        }
        self.legal_cache.as_ref().unwrap()
    }

    pub fn play(&mut self, mv: Move) -> Result<(), String> {
        if self.done {
            return Err("deal is over".into());
        }
        self.legal_cache = None;
        let seat = self.to_act as usize;
        if mv.is_pass() {
            if self.leading() {
                return Err("the leader must play".into());
            }
            self.passes += 1;
        } else {
            let tc = self.table.as_ref().map(|m| m.combo);
            if !mv.combo.beats(tc.as_ref()) {
                return Err("does not beat the table".into());
            }
            for &c in &mv.cards {
                match self.hands[seat].iter().position(|&x| x == c) {
                    Some(i) => {
                        self.hands[seat].remove(i);
                    }
                    None => return Err("those cards are not in your hand".into()),
                }
            }
            self.played[seat].extend_from_slice(&mv.cards);
            self.table = Some(mv.clone());
            self.table_seat = Some(seat);
            self.passes = 0;
            if self.hands[seat].is_empty() {
                self.finished.push(seat);
                if self.team_out() {
                    self.history.push((seat, mv));
                    self.finish();
                    return Ok(());
                }
            }
        }
        self.history.push((seat, mv));
        self.advance();
        Ok(())
    }

    fn team_out(&self) -> bool {
        (0..2).any(|t| self.finished.iter().filter(|&&s| team(s) == t).count() == 2)
    }

    fn finish(&mut self) {
        self.done = true;
        let last = *self.finished.last().unwrap();
        for k in 1..4 {
            let s = (last + k) % 4;
            if !self.finished.contains(&s) {
                self.finished.push(s);
            }
        }
        self.to_act = -1;
    }

    fn advance(&mut self) {
        let ts = self.table_seat.unwrap();
        let responders = (0..4).filter(|&s| self.active(s) && s != ts).count();
        if self.passes >= responders {
            let lead = if self.active(ts) { ts } else { partner(ts) };
            self.table = None;
            self.table_seat = None;
            self.passes = 0;
            self.to_act = lead as i32;
            return;
        }
        let mut s = self.to_act as usize;
        for _ in 0..4 {
            s = (s + 1) % 4;
            if self.active(s) {
                break;
            }
        }
        self.to_act = s as i32;
    }

    /// (winning team, levels gained)
    pub fn result(&self) -> (usize, i32) {
        let first = self.finished[0];
        let idx = self.finished.iter().position(|&s| s == partner(first)).unwrap();
        (team(first), UPGRADE[idx])
    }
}
