// [조 추가] 검색 · 필터 · 정렬.  상단 검색바가 /results?q= 로 보낸다.
import Results from './Results'

export default {
  order: 3,
  nav: [],
  routes: [{ path: '/results', element: <Results /> }],
}
