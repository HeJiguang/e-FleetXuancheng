<template>
  <div class="data-management-view">
    <h1>数据管理中心</h1>

    <div class="tabs">
      <button
        v-for="tab in tabs"
        :key="tab.id"
        :class="{ active: activeTab === tab.id }"
        @click="changeTab(tab.id)"
      >
        {{ tab.name }}
      </button>
    </div>

    <div class="toolbar">
      <div class="actions-left">
        <button @click="openAddModal">新增记录</button>
      </div>
      <div class="actions-right">
        <button @click="downloadTemplate">下载模板</button>
        <input type="file" @change="handleFileUpload" ref="fileInput" style="display: none" />
        <button @click="$refs.fileInput.click()">上传数据</button>
      </div>
    </div>

    <div v-if="isLoading" class="loading-container">
        <div class="spinner"></div>
    </div>
    <div v-else-if="error" class="error-container">{{ error }}</div>
    <div v-else>
      <table>
        <thead>
          <tr>
            <th v-for="header in currentHeaders" :key="header.key" @click="changeSort(header.key)" class="sortable">
              {{ header.label }}
               <span v-if="sortBy === header.key">{{ sortOrder === 'desc' ? '▼' : '▲' }}</span>
            </th>
            <th>操作</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="item in tableData" :key="item[currentIdColumn]">
            <td v-for="header in currentHeaders" :key="header.key">
              {{ item[header.key] }}
            </td>
            <td class="actions">
              <button @click="openEditModal(item)">编辑</button>
              <button @click="deleteItem(item[currentIdColumn])" class="delete">删除</button>
            </td>
          </tr>
        </tbody>
      </table>
      <div class="pagination">
        <button @click="changePage(1)" :disabled="pagination.page === 1">首页</button>
        <button @click="changePage(pagination.page - 1)" :disabled="pagination.page === 1">上一页</button>
        <span>第 {{ pagination.page }} 页 / 共 {{ pagination.total_pages }} 页</span>
        <button @click="changePage(pagination.page + 1)" :disabled="pagination.page >= pagination.total_pages">下一页</button>
        <button @click="changePage(pagination.total_pages)" :disabled="pagination.page >= pagination.total_pages">末页</button>
      </div>
    </div>

    <!-- 新增/编辑弹窗 -->
    <div v-if="isModalOpen" class="modal-overlay" @click.self="closeModal">
      <div class="modal-content">
        <h2>{{ isEditing ? '编辑记录' : '新增记录' }}</h2>
        <form @submit.prevent="saveItem">
          <div class="form-group" v-for="header in currentHeaders.filter(h => h.key !== currentIdColumn)" :key="header.key">
            <label :for="header.key">{{ header.label }}</label>
            <input :type="header.type || 'text'" :id="header.key" v-model="currentItem[header.key]">
          </div>
          <div class="modal-actions">
            <button type="button" @click="closeModal">取消</button>
            <button type="submit">保存</button>
          </div>
        </form>
      </div>
    </div>

  </div>
</template>

<script setup>
import { ref, onMounted, computed, watch } from 'vue';

const API_BASE_URL = 'http://127.0.0.1:5000';

const tabs = [
  { id: 'vehicles', name: '车辆信息' },
  { id: 'violations', name: '违章数据' },
  { id: 'maintenance', name: '维保数据' },
  { id: 'monthly_fuel_summary', name: '油耗汇总' }
];

const headers = {
  vehicles: [
    { key: 'vehicle_id', label: 'ID' },
    { key: 'plate_number', label: '车牌号' },
    { key: 'department_id', label: '部门ID', type: 'number' },
    { key: 'manager', label: '车管员' },
    { key: 'brand_model', label: '品牌型号' },
    { key: 'registration_date', label: '注册日期', type: 'date' }
  ],
  violations: [
    { key: 'violation_id', label: 'ID' },
    { key: 'plate_number', label: '车牌号' },
    { key: 'violation_time', label: '违章时间', type: 'datetime-local' },
    { key: 'violation_location', label: '违章地点' },
    { key: 'violation_type_id', label: '违章类型ID', type: 'number' }
  ],
  maintenance: [
      { key: 'maintenance_id', label: 'ID'},
      { key: 'plate_number', label: '车牌号' },
      { key: 'request_time', label: '申请时间', type: 'datetime-local' },
      { key: 'maintenance_cost', label: '维保费用', type: 'number' }
  ],
  monthly_fuel_summary: [
      { key: 'summary_id', label: 'ID'},
      { key: 'plate_number', label: '车牌号' },
      { key: 'year', label: '年份', type: 'number' },
      { key: 'month', label: '月份', type: 'number' },
      { key: 'total_fuel_cost', label: '油耗花费', type: 'number' }
  ]
};

const activeTab = ref('vehicles');
const tableData = ref([]);
const pagination = ref({ page: 1, per_page: 10, total: 0, total_pages: 1 });
const sortBy = ref('');
const sortOrder = ref('asc');
const isLoading = ref(true);
const error = ref(null);

const isModalOpen = ref(false);
const isEditing = ref(false);
const currentItem = ref({});
const fileInput = ref(null);

const currentHeaders = computed(() => headers[activeTab.value]);
const currentIdColumn = computed(() => headers[activeTab.value][0].key);

const fetchData = async () => {
  isLoading.value = true;
  error.value = null;
  try {
    const params = new URLSearchParams({
      page: pagination.value.page,
      per_page: pagination.value.per_page,
      sort_by: sortBy.value || currentIdColumn.value,
      sort_order: sortOrder.value
    });
    const response = await fetch(`${API_BASE_URL}/api/data/${activeTab.value}?${params.toString()}`);
    if (!response.ok) throw new Error('Failed to fetch data');
    const result = await response.json();
    tableData.value = result.data;
    pagination.value = result.pagination;
  } catch (e) {
    error.value = e.message;
  } finally {
    isLoading.value = false;
  }
};

const changeTab = (tabId) => {
  activeTab.value = tabId;
  pagination.value.page = 1;
  sortBy.value = '';
  sortOrder.value = 'asc';
};

const changePage = (page) => {
  if (page > 0 && page <= pagination.value.total_pages) {
    pagination.value.page = page;
    fetchData();
  }
};

const changeSort = (column) => {
    if (sortBy.value === column) {
        sortOrder.value = sortOrder.value === 'asc' ? 'desc' : 'asc';
    } else {
        sortBy.value = column;
        sortOrder.value = 'asc';
    }
    fetchData();
};

const openAddModal = () => {
  isEditing.value = false;
  currentItem.value = {};
  isModalOpen.value = true;
};

const openEditModal = (item) => {
  isEditing.value = true;
  currentItem.value = { ...item };
  isModalOpen.value = true;
};

const closeModal = () => {
  isModalOpen.value = false;
};

const saveItem = async () => {
  const url = isEditing.value 
    ? `${API_BASE_URL}/api/data/${activeTab.value}/${currentItem.value[currentIdColumn.value]}`
    : `${API_BASE_URL}/api/data/${activeTab.value}`;
  
  const method = isEditing.value ? 'PUT' : 'POST';

  // 移除ID字段，因为通常ID是自增的，不应由用户指定
  const payload = { ...currentItem.value };
  if (!isEditing.value) {
      delete payload[currentIdColumn.value];
  }

  try {
    const response = await fetch(url, {
      method: method,
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    });
    if (!response.ok) throw new Error('Failed to save item');
    closeModal();
    fetchData();
  } catch (e) {
    alert(`Error: ${e.message}`);
  }
};

const deleteItem = async (id) => {
    if (!confirm('确定要删除这条记录吗？')) return;

    try {
        const response = await fetch(`${API_BASE_URL}/api/data/${activeTab.value}/${id}`, {
            method: 'DELETE'
        });
        if (!response.ok) throw new Error('Failed to delete item');
        fetchData();
    } catch (e) {
        alert(`Error: ${e.message}`);
    }
};

const downloadTemplate = () => {
    window.location.href = `${API_BASE_URL}/api/download-template/${activeTab.value}`;
};

const handleFileUpload = async (event) => {
    const file = event.target.files[0];
    if (!file) return;

    const formData = new FormData();
    formData.append('file', file);

    isLoading.value = true;
    try {
        const response = await fetch(`${API_BASE_URL}/api/upload/${activeTab.value}`, {
            method: 'POST',
            body: formData
        });
        const result = await response.json();
        if (!response.ok) throw new Error(result.error || 'File upload failed');
        alert(result.message);
        fetchData();
    } catch (e) {
        alert(`Error: ${e.message}`);
    } finally {
        isLoading.value = false;
        // 重置 input 以便可以再次上传同名文件
        if(fileInput.value) fileInput.value.value = '';
    }
};

watch(activeTab, fetchData, { immediate: true });

</script>

<style scoped>
.data-management-view {
  padding: 20px;
}

h1 {
  margin-bottom: 20px;
}

.tabs {
  display: flex;
  border-bottom: 1px solid #ccc;
  margin-bottom: 20px;
}

.tabs button {
  padding: 10px 20px;
  border: none;
  background: none;
  cursor: pointer;
  font-size: 16px;
  border-bottom: 3px solid transparent;
}

.tabs button.active {
  border-bottom-color: #3498db;
  font-weight: bold;
}

.toolbar {
  display: flex;
  justify-content: space-between;
  margin-bottom: 20px;
}

.toolbar button {
  padding: 8px 15px;
  border: 1px solid #3498db;
  background-color: #3498db;
  color: white;
  border-radius: 4px;
  cursor: pointer;
}
.toolbar .actions-right {
    display: flex;
    gap: 10px;
}

table {
  width: 100%;
  border-collapse: collapse;
}

th, td {
  border: 1px solid #ddd;
  padding: 8px;
  text-align: left;
}

th {
  background-color: #f2f2f2;
}

th.sortable {
    cursor: pointer;
}

.actions {
  display: flex;
  gap: 10px;
}

.actions button {
  padding: 5px 10px;
  border: 1px solid #ccc;
  background-color: #f0f0f0;
  cursor: pointer;
}
.actions button.delete {
    background-color: #e74c3c;
    color: white;
    border-color: #e74c3c;
}

.pagination {
  margin-top: 20px;
  display: flex;
  justify-content: center;
  align-items: center;
  gap: 10px;
}

.modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  background-color: rgba(0, 0, 0, 0.5);
  display: flex;
  justify-content: center;
  align-items: center;
}

.modal-content {
  background: white;
  padding: 20px;
  border-radius: 8px;
  width: 500px;
}

.form-group {
  margin-bottom: 15px;
}

.form-group label {
  display: block;
  margin-bottom: 5px;
}

.form-group input {
  width: 100%;
  padding: 8px;
  box-sizing: border-box;
}

.modal-actions {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
  margin-top: 20px;
}
.loading-container {
    display: flex;
    justify-content: center;
    padding: 40px;
}
.spinner {
    border: 4px solid #f3f3f3;
    border-top: 4px solid #3498db;
    border-radius: 50%;
    width: 40px;
    height: 40px;
    animation: spin 1s linear infinite;
}
@keyframes spin {
    0% { transform: rotate(0deg); }
    100% { transform: rotate(360deg); }
}
</style>
