<script setup>
import { RouterLink, RouterView } from 'vue-router'
</script>

<template>
  <header class="top-nav">
    <h1>宣城车e管</h1>
    <nav>
      <RouterLink to="/">整体概览</RouterLink>
      <RouterLink to="/departments">部门总览</RouterLink>
      <RouterLink to="/vehicles">车辆总览</RouterLink>
      <RouterLink to="/data-management">数据管理</RouterLink>
    </nav>
  </header>

  <main class="main-content">
    <RouterView />
  </main>
</template>

<style scoped>
/* Scoped styles for the main App component shell */
.top-nav {
  background-color: #ffffff;
  padding: 0 40px;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
  display: flex;
  justify-content: space-between;
  align-items: center;
  height: 64px;
}

.top-nav h1 {
  font-size: 22px;
  color: #333;
  margin: 0;
}

.top-nav nav {
  display: flex;
  gap: 20px;
}

.top-nav a {
  text-decoration: none;
  color: #555;
  font-size: 16px;
  font-weight: 500;
  padding: 20px 10px;
  border-bottom: 3px solid transparent;
  transition: color 0.3s, border-bottom-color 0.3s;
}

.top-nav a:hover {
  color: #3498db;
}

.top-nav a.router-link-exact-active {
  color: #3498db;
  border-bottom-color: #3498db;
}

.main-content {
    padding: 20px 40px;
}
</style>
