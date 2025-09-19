<script setup>
import { ref, watch, onMounted, onUnmounted } from 'vue';
import { RouterLink, RouterView, useRouter } from 'vue-router'

const router = useRouter();
const searchQuery = ref('');
const searchResults = ref([]);
const showResults = ref(false);
const isSearching = ref(false);
let debounceTimer = null;
const searchContainer = ref(null);

watch(searchQuery, (newQuery) => {
  clearTimeout(debounceTimer);
  if (newQuery.trim().length === 0) {
    searchResults.value = [];
    isSearching.value = false;
    return;
  }
  isSearching.value = true;
  debounceTimer = setTimeout(() => {
    performSearch(newQuery);
  }, 300); // 300ms debounce
});

const performSearch = async (query) => {
  try {
    const response = await fetch(`http://127.0.0.1:5000/api/search?q=${encodeURIComponent(query)}`);
    if (!response.ok) throw new Error('Search request failed');
    searchResults.value = await response.json();
  } catch (error) {
    console.error('Search error:', error);
    searchResults.value = [];
  } finally {
    isSearching.value = false;
  }
};

const navigateTo = (result) => {
  const url = result.type === 'department'
    ? `/department/${result.id}`
    : `/vehicle/${encodeURIComponent(result.id)}`;
  
  router.push(url);
  
  searchQuery.value = '';
  searchResults.value = [];
  showResults.value = false;
};

const handleClickOutside = (event) => {
  if (searchContainer.value && !searchContainer.value.contains(event.target)) {
    showResults.value = false;
  }
};

onMounted(() => {
  document.addEventListener('click', handleClickOutside);
});

onUnmounted(() => {
  document.removeEventListener('click', handleClickOutside);
});
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
    <div class="search-container" ref="searchContainer">
        <input 
          type="text" 
          v-model="searchQuery" 
          @focus="showResults = true"
          placeholder="搜索部门、车辆..."
        >
        <ul v-if="showResults && (searchQuery.length > 0)" class="search-results">
          <li v-if="isSearching" class="info-item">正在搜索...</li>
          <li v-else-if="searchResults.length === 0" class="info-item">无匹配结果</li>
          <li v-for="result in searchResults" :key="`${result.type}-${result.id}`" @mousedown.prevent="navigateTo(result)">
            <span :class="['result-type', result.type]">{{ result.type === 'department' ? '部门' : '车辆' }}</span>
            <span class="result-name">{{ result.name }}</span>
          </li>
        </ul>
      </div>
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
  /* (修改) 移除 justify-content 来允许搜索框在右侧 */
  align-items: center;
  height: 64px;
}

.top-nav h1 {
  font-size: 22px;
  color: #333;
  margin: 0;
  margin-right: 40px; /* (新增) 增加右边距 */
}

.top-nav nav {
  display: flex;
  gap: 20px;
  /* (新增) 让导航占据可用空间，将搜索框推到右边 */
  flex-grow: 1;
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

/* (新增) 搜索框相关样式 */
.search-container {
  position: relative;
}

.search-container input {
  padding: 8px 15px;
  border-radius: 20px;
  border: 1px solid #ddd;
  width: 220px;
  font-size: 14px;
  transition: all 0.3s ease;
}

.search-container input:focus {
  outline: none;
  border-color: #3498db;
  box-shadow: 0 0 0 2px rgba(52, 152, 219, 0.2);
  width: 280px;
}

.search-results {
  position: absolute;
  top: 110%;
  right: 0;
  width: 320px;
  background: white;
  border: 1px solid #e0e0e0;
  border-radius: 8px;
  list-style: none;
  padding: 8px 0;
  margin: 0;
  box-shadow: 0 5px 15px rgba(0,0,0,0.1);
  z-index: 1000;
  max-height: 400px;
  overflow-y: auto;
}

.search-results li {
  padding: 10px 15px;
  cursor: pointer;
  display: flex;
  align-items: center;
  transition: background-color 0.2s;
}

.search-results li:hover {
  background-color: #f5f9fd;
}

.search-results .info-item {
  color: #888;
  font-style: italic;
  cursor: default;
}
.search-results .info-item:hover {
  background-color: transparent;
}

.result-type {
  font-size: 12px;
  font-weight: 500;
  color: white;
  padding: 3px 8px;
  border-radius: 4px;
  margin-right: 12px;
  flex-shrink: 0;
}
.result-type.department {
  background-color: #3498db;
}
.result-type.vehicle {
  background-color: #2ecc71;
}

.result-name {
  color: #333;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
</style>
