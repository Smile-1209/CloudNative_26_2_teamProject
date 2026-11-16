import { useEffect, useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import { api } from '../../api'
import * as Ic from '../../components/Icons'
import { VideoRow } from '../../components/VideoCard'
import { Empty } from '../../components/ui'

// [조 추가] 검색 결과 + 필터.  필터 값은 주소(?q=&date=&duration=&sort=&category=)에 둔다 → 뒤로가기·링크 공유가 된다.
const GROUPS = [
  ['date', '업로드 날짜', [['hour', '지난 1시간'], ['today', '오늘'], ['week', '이번 주'], ['month', '이번 달'], ['year', '올해']]],
  ['duration', '길이', [['short', '4분 미만'], ['medium', '4~20분'], ['long', '20분 초과']]],
  ['sort', '정렬기준', [['relevance', '관련성'], ['latest', '업로드 날짜'], ['views', '조회수'], ['likes', '좋아요']]],
]

export default function Results() {
  const [sp, setSp] = useSearchParams()
  const q = sp.get('q') || ''
  const [d, setD] = useState(null)
  const [open, setOpen] = useState(false)
  const [categories, setCategories] = useState([])

  useEffect(() => { api.get('/api/videos/categories').then(setCategories).catch(() => {}) }, [])
  useEffect(() => {
    setD(null)
    api.get(`/api/search/?${sp.toString()}`).then(setD).catch(() => setD({ items: [], total: 0, categories: {} }))
  }, [sp])

  const setParam = (k, v) => {
    const next = new URLSearchParams(sp)
    if (!v || next.get(k) === v || (k === 'sort' && v === 'relevance')) next.delete(k)
    else next.set(k, v)
    setSp(next)
  }
  const active = GROUPS.filter(([k]) => sp.get(k)).length + (sp.get('category') ? 1 : 0)

  return (
    <div style={{ maxWidth: 1096, margin: '0 auto' }}>
      <div className="chips" style={{ alignItems: 'center' }}>
        <button className={`chip ${!sp.get('category') ? 'on' : ''}`} onClick={() => setParam('category', '')}>전체</button>
        {categories.map((c) => (
          <button key={c} className={`chip ${sp.get('category') === c ? 'on' : ''}`} onClick={() => setParam('category', c)}>
            {c}{d?.categories?.[c] ? <span className="chip-n">{d.categories[c]}</span> : null}
          </button>
        ))}
        <button className={`pill filter-btn ${open ? 'on' : ''}`} onClick={() => setOpen((o) => !o)}>
          <Ic.Filter /> 필터{active > 0 && ` · ${active}`}
        </button>
      </div>

      {open && (
        <div className="filters">
          {GROUPS.map(([k, label, opts]) => (
            <div key={k}>
              <h4>{label}</h4>
              {opts.map(([v, text]) => {
                const on = (sp.get(k) || (k === 'sort' ? 'relevance' : '')) === v
                return <button key={v} className={on ? 'on' : ''} onClick={() => setParam(k, v)}>{text}{on && k !== 'sort' && <Ic.Close size={14} />}</button>
              })}
            </div>
          ))}
        </div>
      )}

      {d === null ? null : d.items.length === 0
        ? <Empty>{q ? `"${q}"에 대한 검색 결과가 없습니다.` : '조건에 맞는 동영상이 없습니다.'}{active > 0 && <><br /><button className="btn ghost" style={{ marginTop: 16 }} onClick={() => setSp(q ? { q } : {})}>필터 모두 지우기</button></>}</Empty>
        : <>
          <div className="muted" style={{ marginBottom: 12 }}>검색 결과 {d.total}개</div>
          {d.items.map((v) => <VideoRow key={v.id} v={v} big />)}
        </>}
    </div>
  )
}
