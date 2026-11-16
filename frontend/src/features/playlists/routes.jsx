// [조 추가] 재생목록 · 나중에 볼 동영상.  사이드바 '내 페이지' 에 붙는다 (auth: 로그인해야 보임).
import Playlist from './Playlist'
import Playlists from './Playlists'

export default {
  order: 4,
  nav: [
    { to: '/playlists', label: '재생목록', icon: 'playlist', section: 'you', auth: true },
    { to: '/playlist/WL', label: '나중에 볼 동영상', icon: 'watchlater', section: 'you', auth: true },
  ],
  routes: [
    { path: '/playlists', element: <Playlists /> },
    { path: '/playlist/:id', element: <Playlist /> },
  ],
}
