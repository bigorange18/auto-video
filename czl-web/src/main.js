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

const SITE_NAME = '小狐务器'
router.afterEach((to) => {
  const titles = { home: SITE_NAME, admin: `管理后台 - ${SITE_NAME}` }
  document.title = titles[to.name] || `${to.meta.title || '文章'} - ${SITE_NAME}`
})

createApp(App).use(router).mount('#app')
