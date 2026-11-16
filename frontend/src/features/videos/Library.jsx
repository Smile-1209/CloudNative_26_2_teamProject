import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { api } from '../../api'
import { useAuth } from '../../auth'
import RequireLogin from '../../components/RequireLogin'
import VideoCard from '../../components/VideoCard'
import { Empty } from '../../components/ui'
import * as localHistory from '../../localHistory'

// 구독 피드 · 시청 기록 · 내 동영상 · 좋아요 — 같은 화면, API 만 다르다
// [조 추가] 시청 기록은 로그인 안 해도 보인다 — 이 브라우저(localStorage)에 남은 기록
export default function Library({ kind, title, empty }) {
  const { me } = useAuth()
  const [videos, setVideos] = useState(null)
  const guestHistory = kind === 'history' && me === null

  useEffect(() => {
    if (me === undefined) return
    setVideos(null)
    if (guestHistory) {
      const ids = localHistory.list().map((h) => h.vid)
      if (!ids.length) { setVideos([]); return }
      api.get(`/api/videos/by-ids?ids=${ids.join(',')}`).then(setVideos).catch(() => setVideos([]))
      return
    }
    if (!me) return
    api.get(`/api/videos/${kind}`).then(setVideos).catch(() => setVideos([]))
  }, [kind, me, guestHistory])

  const grid = videos === null ? null : videos.length === 0
    ? <Empty>{empty}</Empty>
    : <div className="vgrid">{videos.map((v) => <VideoCard key={v.id} v={v} hideChannel={kind === 'mine'} />)}</div>

  if (guestHistory) {
    return (
      <>
        <div className="row between" style={{ marginBottom: 16 }}>
          <h1 style={{ margin: 0 }}>{title}</h1>
          {videos?.length > 0 && (
            <button className="btn ghost" onClick={() => { localHistory.clear(); setVideos([]) }}>시청 기록 모두 지우기</button>
          )}
        </div>
        <div className="notice">
          로그인하지 않은 상태의 시청 기록은 <b>이 브라우저에만</b> 저장됩니다.{' '}
          <Link to="/login" state={{ from: '/history' }}>로그인</Link>하면 내 계정 기록으로 합쳐집니다.
        </div>
        {grid}
      </>
    )
  }

  return (
    <RequireLogin>
      <h1>{title}</h1>
      {grid}
    </RequireLogin>
  )
}
