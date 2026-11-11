// [조 추가] 비로그인 시청 기록 — 서버가 아니라 이 브라우저(localStorage)에만 남는다.  (V2 아키텍처의 Browser Local Storage)
// 로그인하면 auth.jsx 가 서버(/api/videos/history/merge)로 합치고 비운다.
const KEY = 'tubelite.history'
const MAX = 100

export function list() {
  try { return JSON.parse(localStorage.getItem(KEY)) || [] } catch { return [] }   // [{vid, at}] 최신순
}

function save(items) {
  try { localStorage.setItem(KEY, JSON.stringify(items.slice(0, MAX))) } catch { /* 사생활 보호 모드 등 */ }
}

export function add(vid) {
  save([{ vid, at: new Date().toISOString() }, ...list().filter((h) => h.vid !== vid)])
}

export function remove(vid) {
  save(list().filter((h) => h.vid !== vid))
}

export function clear() {
  try { localStorage.removeItem(KEY) } catch { /* ignore */ }
}
