<script setup>
const year = new Date().getFullYear()
</script>

<template>
  <footer class="site-footer">
    <div class="footer-inner">
      <span>&copy; 2024&ndash;{{ year }} 大橘. All rights reserved.</span>
      <div class="footer-links">
        <router-link to="/guestbook">留言板</router-link>
        <a href="/api/public/rss" target="_blank">RSS</a>
        <router-link to="/admin">管理</router-link>
      </div>
    </div>
  </footer>
</template>
