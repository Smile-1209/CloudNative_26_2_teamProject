import { useEffect, useState } from 'react'
import { api } from '../../api'
import * as Ic from '../../components/Icons'
import { ErrorBox } from '../../components/ui'

// 시청 페이지의 '저장' → 재생목록 체크 · 새 재생목록 만들기 (유튜브의 '저장' 창)
export default function SaveDialog({ videoId, onClose }) {
  const [lists, setLists] = useState(null)
  const [creating, setCreating] = useState(false)
  const [title, setTitle] = useState('')
  const [visibility, setVisibility] = useState('private')
  const [err, setErr] = useState(null)

  useEffect(() => { api.get(`/api/playlists/saved/${videoId}`).then(setLists).catch(setErr) }, [videoId])
  useEffect(() => {
    const esc = (e) => e.key === 'Escape' && onClose()
    window.addEventListener('keydown', esc)
    return () => window.removeEventListener('keydown', esc)
  }, [onClose])

  const toggle = async (p) => {
    try {
      const r = await api.post(`/api/playlists/${p.id}/toggle`, { video_id: videoId })
      setLists((ls) => ls.map((x) => (x.id === p.id ? { ...x, has: r.has } : x)))
    } catch (e) { setErr(e) }
  }
  const create = async (e) => {
    e.preventDefault()
    try {
      const p = await api.post('/api/playlists/', { title, visibility, video_id: videoId })
      setLists((ls) => [...ls, { ...p, has: true }]); setCreating(false); setTitle('')
    } catch (e) { setErr(e) }
  }

  return (
    <div className="modal-bg" onClick={onClose}>
      <div className="modal" onClick={(e) => e.stopPropagation()}>
        <div className="modal-head">
          <b>동영상 저장...</b>
          <button className="ibtn" onClick={onClose} aria-label="닫기"><Ic.Close /></button>
        </div>
        <ErrorBox error={err} />
        <div className="savelist">
          {lists?.map((p) => (
            <label key={p.id}>
              <input type="checkbox" checked={p.has} onChange={() => toggle(p)} />
              <span>{p.title}</span>
              {p.visibility === 'public' ? <Ic.Globe size={18} /> : <Ic.Lock size={18} />}
            </label>
          ))}
        </div>
        {creating ? (
          <form className="form" onSubmit={create} style={{ marginTop: 12 }}>
            <div className="field"><span>이름</span><input value={title} onChange={(e) => setTitle(e.target.value)} maxLength={150} autoFocus placeholder="재생목록 제목 입력..." /></div>
            <div className="field"><span>공개 범위</span>
              <select value={visibility} onChange={(e) => setVisibility(e.target.value)}>
                <option value="private">비공개 — 나만 볼 수 있음</option>
                <option value="public">공개 — 링크가 있는 누구나</option>
              </select>
            </div>
            <div className="row" style={{ justifyContent: 'flex-end' }}>
              <button type="button" className="btn ghost" onClick={() => setCreating(false)}>취소</button>
              <button className="btn accent" disabled={!title.trim()}>만들기</button>
            </div>
          </form>
        ) : (
          <button className="newlist" onClick={() => setCreating(true)}>＋ 새 재생목록 만들기</button>
        )}
      </div>
    </div>
  )
}
