import { createApp } from 'vue'
import { createRouter, createWebHistory } from 'vue-router'
import App from './App.vue'
import './styles.css'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/', name: 'home', component: () => import('./views/HomeView.vue') },
    { path: '/admin', name: 'admin', component: () => import('./views/AdminView.vue') },
    { path: '/article/:id', name: 'article', component: () => import('./views/ArticleView.vue') },
  ],
})

router.afterEach(() => {
  window.scrollTo({ top: 0, behavior: 'instant' })
})

const SITE = '大橘'
router.afterEach((to) => {
  document.title = to.name === 'home' ? SITE : to.name === 'admin' ? `管理后台 - ${SITE}` : (to.meta.title || '文章') + ` - ${SITE}`
})

createApp(App).use(router).mount('#app')
