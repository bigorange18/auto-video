import { createApp } from 'vue'
import { createRouter, createWebHistory } from 'vue-router'
import App from './App.vue'
import './styles.css'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/', name: 'home', component: () => import('./views/HomeView.vue') },
    { path: '/about', name: 'about', component: () => import('./views/AboutView.vue') },
    { path: '/projects', name: 'projects', component: () => import('./views/ProjectsView.vue') },
    { path: '/admin', name: 'admin', component: () => import('./views/AdminView.vue') },
    { path: '/article/:id', name: 'article', component: () => import('./views/ArticleView.vue') },
    { path: '/:pathMatch(.*)*', name: 'not-found', component: () => import('./views/NotFoundView.vue') },
    { path: '/tag/:tagName', name: 'tag', component: () => import('./views/TagView.vue') },
    { path: '/tags', name: 'tags', component: () => import('./views/TagView.vue') },
  ],
})

router.afterEach(() => {
  window.scrollTo({ top: 0, behavior: 'instant' })
})

const SITE = '大橘'
router.afterEach((to) => {
  const titles = { home: SITE, admin: `管理后台 - ${SITE}`, about: `关于 - ${SITE}`, projects: `项目 - ${SITE}` }
  document.title = titles[to.name] || (to.meta.title || '文章') + ` - ${SITE}`
})

createApp(App).use(router).mount('#app')
