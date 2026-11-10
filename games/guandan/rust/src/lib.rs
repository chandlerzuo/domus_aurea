//! Python bindings for the guandan Rust core. `RsDeal` mirrors guandan.game.Deal; the batch
//! functions encode and advance many deals per call so the Python side stays out of the hot loop.

mod combos;
mod deal;
mod features;

use numpy::{PyArray1, PyArray2, PyArrayMethods};
use pyo3::exceptions::PyValueError;
use pyo3::prelude::*;

use combos::{legal_moves, Combo, Move, N_CARDS};
use deal::Deal;

type MoveTuple = (u8, i32, u8, Vec<u8>);

fn to_tuple(m: &Move) -> MoveTuple {
    (m.combo.kind, m.combo.value, m.combo.size, m.cards.clone())
}

fn from_tuple(t: MoveTuple) -> Move {
    Move { combo: Combo { kind: t.0, value: t.1, size: t.2 }, cards: t.3 }
}

fn err(e: String) -> PyErr {
    PyValueError::new_err(e)
}

struct SplitMix(u64);

impl SplitMix {
    fn next(&mut self) -> u64 {
        self.0 = self.0.wrapping_add(0x9E37_79B9_7F4A_7C15);
        let mut z = self.0;
        z = (z ^ (z >> 30)).wrapping_mul(0xBF58_476D_1CE4_E5B9);
        z = (z ^ (z >> 27)).wrapping_mul(0x94D0_49BB_1331_11EB);
        z ^ (z >> 31)
    }
}

#[pyclass(module = "guandan_core")]
#[derive(Clone)]
struct RsDeal {
    d: Deal,
    version: u8, // feature version for the encode_* methods (1 or 2)
}

#[pymethods]
impl RsDeal {
    #[new]
    #[pyo3(signature = (hands, level, leader, team_levels=(0, 0), level_team=None, version=1))]
    fn new(hands: Vec<Vec<u8>>, level: u8, leader: usize, team_levels: (u8, u8), level_team: Option<u8>,
           version: u8) -> PyResult<Self> {
        if hands.len() != 4 || leader > 3 || level > 12 {
            return Err(err("need 4 hands, leader 0..3, level 0..12".into()));
        }
        Ok(RsDeal { d: Deal::new(hands, level, leader, [team_levels.0, team_levels.1], level_team), version })
    }

    /// A deal in the middle of play. `hands` must already hold the (possibly sampled) hands of all
    /// four seats; `history` is [(seat, (kind, value, size, cards))].
    #[staticmethod]
    #[pyo3(signature = (hands, level, to_act, team_levels, level_team, table, table_seat, passes, finished, history, played, version=1))]
    #[allow(clippy::too_many_arguments)]
    fn from_state(hands: Vec<Vec<u8>>, level: u8, to_act: usize, team_levels: (u8, u8), level_team: Option<u8>,
                  table: Option<MoveTuple>, table_seat: Option<usize>, passes: usize, finished: Vec<usize>,
                  history: Vec<(usize, MoveTuple)>, played: Vec<Vec<u8>>, version: u8) -> PyResult<Self> {
        if hands.len() != 4 || played.len() != 4 || to_act > 3 || level > 12 {
            return Err(err("need 4 hands and 4 played lists, to_act 0..3, level 0..12".into()));
        }
        let history = history.into_iter().map(|(s, m)| (s, from_tuple(m))).collect();
        Ok(RsDeal {
            d: Deal::from_state(hands, level, to_act, [team_levels.0, team_levels.1], level_team,
                                table.map(from_tuple), table_seat, passes, finished, history, played),
            version,
        })
    }

    #[getter] fn version(&self) -> u8 { self.version }
    #[getter] fn done(&self) -> bool { self.d.done }
    #[getter] fn to_act(&self) -> i32 { self.d.to_act }
    #[getter] fn level(&self) -> u8 { self.d.level }
    #[getter] fn leading(&self) -> bool { self.d.leading() }
    #[getter] fn passes(&self) -> usize { self.d.passes }
    #[getter] fn table_seat(&self) -> Option<usize> { self.d.table_seat }
    #[getter] fn finished(&self) -> Vec<usize> { self.d.finished.clone() }
    #[getter] fn hands(&self) -> Vec<Vec<u8>> { self.d.hands.to_vec() }
    #[getter] fn played(&self) -> Vec<Vec<u8>> { self.d.played.to_vec() }
    #[getter] fn counts(&self) -> Vec<usize> { self.d.hands.iter().map(|h| h.len()).collect() }
    #[getter] fn team_levels(&self) -> (u8, u8) { (self.d.team_levels[0], self.d.team_levels[1]) }
    #[getter] fn level_team(&self) -> Option<u8> { self.d.level_team }
    #[getter] fn table(&self) -> Option<MoveTuple> { self.d.table.as_ref().map(to_tuple) }
    #[getter]
    fn history(&self) -> Vec<(usize, MoveTuple)> {
        self.d.history.iter().map(|(s, m)| (*s, to_tuple(m))).collect()
    }

    fn result(&self) -> PyResult<(usize, i32)> {
        if !self.d.done {
            return Err(err("deal is not over".into()));
        }
        Ok(self.d.result())
    }

    fn legal(&mut self) -> PyResult<Vec<MoveTuple>> {
        self.need_turn()?;
        Ok(self.d.legal().iter().map(to_tuple).collect())
    }

    fn n_legal(&mut self) -> PyResult<usize> {
        self.need_turn()?;
        Ok(self.d.legal().len())
    }

    /// Play the i-th legal move.
    fn play_index(&mut self, i: usize) -> PyResult<()> {
        self.need_turn()?;
        let mv = self.d.legal().get(i).cloned().ok_or_else(|| err("move index out of range".into()))?;
        self.d.play(mv).map_err(err)
    }

    /// Play an explicit move (kind, value, size, cards); validated against the table and the hand.
    fn play(&mut self, kind: u8, value: i32, size: u8, cards: Vec<u8>) -> PyResult<()> {
        self.need_turn()?;
        self.d.play(from_tuple((kind, value, size, cards))).map_err(err)
    }

    #[pyo3(signature = (seat, version=None))]
    fn encode_state<'py>(&self, py: Python<'py>, seat: usize, version: Option<u8>) -> Bound<'py, PyArray1<u8>> {
        let version = version.unwrap_or(self.version);
        let mut v = vec![0u8; features::state_dim(version)];
        features::encode_state(&self.d, seat, version, &mut v);
        PyArray1::from_vec_bound(py, v)
    }

    #[pyo3(signature = (version=None))]
    fn encode_actions<'py>(&mut self, py: Python<'py>, version: Option<u8>) -> PyResult<Bound<'py, PyArray2<u8>>> {
        self.need_turn()?;
        let (level, version) = (self.d.level, version.unwrap_or(self.version));
        let hand = self.d.hands[self.d.to_act as usize].clone();
        let ad = features::action_dim(version);
        let moves = self.d.legal();
        let mut flat = vec![0u8; moves.len() * ad];
        for (m, row) in moves.iter().zip(flat.chunks_mut(ad)) {
            features::encode_action(m, &hand, level, version, row);
        }
        let n = moves.len();
        PyArray1::from_vec_bound(py, flat).reshape([n, ad])
    }

    fn encode_oracle<'py>(&self, py: Python<'py>, seat: usize) -> Bound<'py, PyArray1<u8>> {
        let mut v = vec![0u8; features::ORACLE_DIM];
        features::encode_oracle(&self.d, seat, &mut v);
        PyArray1::from_vec_bound(py, v)
    }

    fn copy(&self) -> RsDeal {
        self.clone()
    }

    /// A copy in which the other three hands are redealt at random from the cards `seat` cannot
    /// see (same hand sizes). Used by search to sample worlds consistent with the public play.
    fn resample(&self, seat: usize, seed: u64) -> RsDeal {
        let mut c = self.clone();
        let mut unseen: Vec<u8> = (0..N_CARDS as u8)
            .filter(|x| !self.d.hands[seat].contains(x) && !self.d.played.iter().any(|p| p.contains(x)))
            .collect();
        let mut rng = SplitMix(seed);
        for i in (1..unseen.len()).rev() {
            let j = (rng.next() % (i as u64 + 1)) as usize;
            unseen.swap(i, j);
        }
        let mut at = 0;
        let level = self.d.level;
        for s in 0..4 {
            if s != seat {
                let n = self.d.hands[s].len();
                let mut h = unseen[at..at + n].to_vec();
                at += n;
                h.sort_by_key(|&x| combos::sort_key(x, level));
                c.d.hands[s] = h;
            }
        }
        c.d.reset_cache();
        c
    }
}

impl RsDeal {
    fn need_turn(&self) -> PyResult<()> {
        if self.d.done || self.d.to_act < 0 {
            return Err(err("deal is over".into()));
        }
        Ok(())
    }
}

/// Legal moves from a hand (card ids in hand order) over an optional table combo (kind, value, size).
#[pyfunction]
#[pyo3(signature = (hand, level, table=None))]
fn legal_moves_py(hand: Vec<u8>, level: u8, table: Option<(u8, i32, u8)>) -> Vec<MoveTuple> {
    let tc = table.map(|t| Combo { kind: t.0, value: t.1, size: t.2 });
    legal_moves(&hand, level, tc.as_ref()).iter().map(to_tuple).collect()
}

/// States, flat legal-move rows and move counts for the player to act in each deal.
#[pyfunction]
#[pyo3(signature = (deals, version=1))]
fn batch_encode<'py>(
    py: Python<'py>,
    deals: Vec<PyRefMut<'py, RsDeal>>,
    version: u8,
) -> PyResult<(Bound<'py, PyArray2<u8>>, Bound<'py, PyArray2<u8>>, Bound<'py, PyArray1<i32>>)> {
    let b = deals.len();
    let (sd, ad) = (features::state_dim(version), features::action_dim(version));
    let mut s = vec![0u8; b * sd];
    let mut a: Vec<u8> = Vec::new();
    let mut n = Vec::with_capacity(b);
    for (mut dl, row) in deals.into_iter().zip(s.chunks_mut(sd)) {
        dl.need_turn()?;
        let seat = dl.d.to_act as usize;
        features::encode_state(&dl.d, seat, version, row);
        let hand = dl.d.hands[seat].clone();
        let level = dl.d.level;
        let moves = dl.d.legal();
        let start = a.len();
        a.resize(start + moves.len() * ad, 0);
        for (m, r) in moves.iter().zip(a[start..].chunks_mut(ad)) {
            features::encode_action(m, &hand, level, version, r);
        }
        n.push(moves.len() as i32);
    }
    let rows = a.len() / ad;
    Ok((
        PyArray1::from_vec_bound(py, s).reshape([b, sd])?,
        PyArray1::from_vec_bound(py, a).reshape([rows, ad])?,
        PyArray1::from_vec_bound(py, n),
    ))
}

/// Oracle targets (the other players' hidden hands) from each acting player's view.
#[pyfunction]
fn batch_oracle<'py>(py: Python<'py>, deals: Vec<PyRef<'py, RsDeal>>) -> PyResult<Bound<'py, PyArray2<u8>>> {
    let b = deals.len();
    let mut o = vec![0u8; b * features::ORACLE_DIM];
    for (dl, row) in deals.iter().zip(o.chunks_mut(features::ORACLE_DIM)) {
        dl.need_turn()?;
        features::encode_oracle(&dl.d, dl.d.to_act as usize, row);
    }
    PyArray1::from_vec_bound(py, o).reshape([b, features::ORACLE_DIM])
}

/// Play move `idx[k]` in deal k.
#[pyfunction]
fn batch_play(deals: Vec<PyRefMut<'_, RsDeal>>, idx: Vec<usize>) -> PyResult<()> {
    if deals.len() != idx.len() {
        return Err(err("deals and idx differ in length".into()));
    }
    for (mut dl, i) in deals.into_iter().zip(idx) {
        dl.need_turn()?;
        let mv = dl.d.legal().get(i).cloned().ok_or_else(|| err("move index out of range".into()))?;
        dl.d.play(mv).map_err(err)?;
    }
    Ok(())
}

#[pymodule]
fn guandan_core(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_class::<RsDeal>()?;
    m.add_function(wrap_pyfunction!(legal_moves_py, m)?)?;
    m.add_function(wrap_pyfunction!(batch_encode, m)?)?;
    m.add_function(wrap_pyfunction!(batch_oracle, m)?)?;
    m.add_function(wrap_pyfunction!(batch_play, m)?)?;
    m.add("STATE_DIM", features::STATE_DIM)?;
    m.add("ACTION_DIM", features::ACTION_DIM)?;
    m.add("STATE_DIM_V2", features::STATE_DIM_V2)?;
    m.add("ACTION_DIM_V2", features::ACTION_DIM_V2)?;
    m.add("ORACLE_DIM", features::ORACLE_DIM)?;
    Ok(())
}
