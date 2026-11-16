import { useEffect, useState } from 'react'
import { api } from '../../api'
import VideoCard from '../../components/VideoCard'
import { Empty } from '../../components/ui'

const CHIPS = [['latest', '전체'], ['trending', '인기'], ['popular', '조회수순']]

export default function Home() {
  const [sort, setSort] = useState('latest')
  const [category, setCategory] = useState('')     // [조 추가] 카테고리 칩
  const [categories, setCategories] = useState([])
  const [videos, setVideos] = useState(null)

  useEffect(() => { api.get('/api/videos/categories').then(setCategories).catch(() => {}) }, [])
  useEffect(() => {
    setVideos(null)
    api.get(`/api/videos/?sort=${sort}&category=${encodeURIComponent(category)}`).then(setVideos).catch(() => setVideos([]))
  }, [sort, category])

  return (
    <>
      <div className="chips">
        {CHIPS.map(([k, label]) => (
          <button key={k} className={`chip ${sort === k ? 'on' : ''}`} onClick={() => setSort(k)}>{label}</button>
        ))}
        <span className="chip-sep" />
        {categories.map((c) => (
          <button key={c} className={`chip ${category === c ? 'on' : ''}`} onClick={() => setCategory((x) => (x === c ? '' : c))}>{c}</button>
        ))}
      </div>
      {videos === null ? null : videos.length === 0
        ? <Empty>{sort === 'trending' ? '인기 집계가 아직 없습니다. (매일 서버 안 스케줄러가 집계합니다)' : category ? `'${category}' 카테고리에 동영상이 없습니다.` : '아직 동영상이 없습니다.'}</Empty>
        : <div className="vgrid">{videos.map((v) => <VideoCard key={v.id} v={v} />)}</div>}
    </>
  )
}
