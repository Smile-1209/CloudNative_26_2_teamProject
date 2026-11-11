import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { api } from '../../api'
import * as Ic from '../../components/Icons'
import RequireLogin from '../../components/RequireLogin'
import { Empty } from '../../components/ui'
import { timeAgo } from '../../format'

// 내 재생목록 (나중에 볼 동영상 + 내가 만든 것)
function PlaylistCard({ p }) {
  const to = p.kind === 'watch_later' ? '/playlist/WL' : `/playlist/${p.id}`
  return (
    <div className="vcard">
      <Link to={to} className="plthumb">
        <div className="vthumb">{p.thumb_url ? <img src={p.thumb_url} alt="" /> : <div className="vthumb-ph" />}</div>
        <span className="plcount"><Ic.Playlist size={18} /> 동영상 {p.count}개</span>
      </Link>
      <div className="vtext" style={{ marginTop: 12 }}>
        <Link to={to} className="vtitle">{p.title}</Link>
        <div className="vsub">{p.visibility === 'public' ? '공개' : '비공개'} · 업데이트 {timeAgo(p.updated_at)}</div>
      </div>
    </div>
  )
}

export default function Playlists() {
  const [lists, setLists] = useState(null)
  useEffect(() => { api.get('/api/playlists/').then(setLists).catch(() => setLists([])) }, [])

  return (
    <RequireLogin>
      <h1>재생목록</h1>
      <p className="muted" style={{ marginTop: -8, marginBottom: 20 }}>시청 페이지의 <b>저장</b> 버튼으로 동영상을 담고 새 재생목록을 만들 수 있습니다.</p>
      {lists === null ? null : lists.length === 0 ? <Empty>재생목록이 없습니다.</Empty>
        : <div className="vgrid">{lists.map((p) => <PlaylistCard key={p.id} p={p} />)}</div>}
    </RequireLogin>
  )
}
