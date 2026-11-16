import { useEffect, useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import { api } from '../../api'
import { useAuth } from '../../auth'
import Avatar from '../../components/Avatar'
import * as Ic from '../../components/Icons'
import RequireLogin from '../../components/RequireLogin'
import { VideoRow } from '../../components/VideoCard'
import { Empty, ErrorBox } from '../../components/ui'
import { timeAgo } from '../../format'

// 재생목록 하나.  주인이면 영상 빼기 · 목록 삭제.  공개 재생목록은 링크로 누구나 본다.
function PlaylistView() {
  const { id } = useParams()
  const { me } = useAuth()
  const nav = useNavigate()
  const [d, setD] = useState(null)
  const [err, setErr] = useState(null)

  useEffect(() => { setD(null); setErr(null); api.get(`/api/playlists/${id}`).then(setD).catch(setErr) }, [id, me])

  if (err && !d) return <Empty>{err.message}</Empty>
  if (!d) return null
  const { playlist: p, owner, videos } = d
  const mine = me?.id === p.owner

  const removeVideo = async (vid) => {
    try {
      await api.post(`/api/playlists/${p.id}/toggle`, { video_id: vid })
      setD((s) => ({ ...s, videos: s.videos.filter((v) => v.id !== vid), playlist: { ...s.playlist, count: s.playlist.count - 1 } }))
    } catch (e) { setErr(e) }
  }
  const remove = async () => {
    if (!window.confirm(`'${p.title}' 재생목록을 삭제할까요?`)) return
    try { await api.post(`/api/playlists/${p.id}/delete`); nav('/playlists') } catch (e) { setErr(e) }
  }
  const share = async () => {
    try { await navigator.clipboard.writeText(`${window.location.origin}/playlist/${p.id}`); alert('링크를 복사했습니다.') } catch { /* ignore */ }
  }

  return (
    <div className="plwrap">
      <aside className="plhead" style={{ background: `linear-gradient(180deg, ${owner.color}aa, #0f0f0f)` }}>
        <div className="vthumb">{videos[0]?.thumb_url ? <img src={videos[0].thumb_url} alt="" /> : <div className="vthumb-ph" />}</div>
        <h1>{p.title}</h1>
        <Link to={`/channel/${owner.id}`} className="row" style={{ gap: 8, fontWeight: 500 }}>
          <Avatar name={owner.name} color={owner.color} size={24} />{owner.name}
        </Link>
        <div className="muted" style={{ fontSize: 13, margin: '8px 0 16px' }}>
          {p.visibility === 'public' ? '공개' : '비공개'} · 동영상 {p.count}개 · 업데이트 {timeAgo(p.updated_at)}
        </div>
        <div className="row">
          {videos[0] && <Link to={`/watch/${videos[0].id}`} className="btn plplay"><Ic.Play size={18} /> 모두 재생</Link>}
          {p.visibility === 'public' && <button className="pill" onClick={share}><Ic.Share /> 공유</button>}
          {mine && p.kind !== 'watch_later' && <button className="pill" onClick={remove}>삭제</button>}
        </div>
      </aside>
      <div>
        <ErrorBox error={err} />
        {videos.length === 0
          ? <Empty>{p.kind === 'watch_later' ? '시청 페이지의 저장 → 나중에 볼 동영상 을 눌러 담아 보세요.' : '이 재생목록에 동영상이 없습니다.'}</Empty>
          : videos.map((v, i) => (
            <div key={v.id} className="plitem">
              <span className="plnum">{i + 1}</span>
              <VideoRow v={v} />
              {mine && <button className="ibtn" title="재생목록에서 삭제" onClick={() => removeVideo(v.id)}><Ic.Close size={20} /></button>}
            </div>
          ))}
      </div>
    </div>
  )
}

export default function Playlist() {
  const { id } = useParams()
  return id === 'WL' ? <RequireLogin><PlaylistView /></RequireLogin> : <PlaylistView />
}
