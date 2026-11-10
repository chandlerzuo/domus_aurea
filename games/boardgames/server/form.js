'use strict';
/* 伺服器端的「表單」：用瀏覽器送回的輸入值，模擬引擎按鈕函式所需的 querySelector。
 * inputs: [{ id, name, type, value, checked, k }]，k 為 data-k。
 * 支援引擎用到的選擇器：#id、input:checked、input[name=x]:checked、input[type=checkbox]:checked */
function makeForm(inputs) {
  const errors = {};
  const wrap = i => ({ value: i.value, checked: !!i.checked, dataset: { k: i.k } });
  const match = sel => {
    let m;
    if ((m = /^#([\w-]+)$/.exec(sel))) {
      const i = inputs.find(x => x.id === m[1]);
      if (i) return [wrap(i)];
      const id = m[1];
      return [{ set textContent(t) { errors[id] = String(t); }, get textContent() { return errors[id] || ''; } }];
    }
    if ((m = /^input(?:\[(name|type)=([\w-]+)\])?(:checked)?$/.exec(sel))) {
      return inputs.filter(i => (!m[1] || i[m[1]] === m[2]) && (!m[3] || i.checked)).map(wrap);
    }
    throw new Error('不支援的選擇器：' + sel);
  };
  return { querySelector: sel => match(sel)[0] || null, querySelectorAll: sel => match(sel), errors };
}
module.exports = { makeForm };
