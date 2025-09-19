<script setup>
import { RouterLink } from 'vue-router'; // (新增)

// (删除) 移除 chart.js
// import Chart from 'chart.js/auto';

// (新增) 导入 ECharts
import { use } from 'echarts/core';
import { CanvasRenderer } from 'echarts/renderers';
import { BarChart } from 'echarts/charts';
import {
  TitleComponent,
  TooltipComponent,
  GridComponent,
  LegendComponent,
  DataZoomComponent, // (新增) 导入 dataZoom 组件
} from 'echarts/components';
import VChart from 'vue-echarts';
import { ref, onMounted, computed } from 'vue';


// (新增) 注册 ECharts 组件
use([
  CanvasRenderer,
  BarChart,
  TitleComponent,
  TooltipComponent,
  GridComponent,
  LegendComponent,
  DataZoomComponent, // (新增) 注册 dataZoom 组件
]);


// Reactive State
const departmentView = ref({
  isLoading: true,
  error: null,
  data: [],
  kpis: {}, // (新增) 存储KPI数据
  activeTab: 'mileage',
  // (新增) 分页状态
  pagination: {
      page: 1,
      per_page: 10,
      total: 0,
      total_pages: 1,
  }
});

// (新增) 统一管理筛选器状态
const filters = ref({
  startMonth: '2025-01',
  endMonth: '2025-06'
});

// (删除) 移除 chart.js 实例
// const charts = {}; 

// (修改) 更新 tabs 定义，加入单位和标签
const tabs = [
  { id: 'mileage', name: '里程管理', unit: '公里', label: '总里程' },
  { id: 'fuel', name: '油耗管理', unit: '升', label: '总油耗' },
  { id: 'violations', name: '违章管理', unit: '次', label: '总违章' },
  { id: 'maintenance', name: '维保管理', unit: '元', label: '总维保费用' }
];

// (恢复) 增加排名计算属性
const departmentRankings = computed(() => {
  if (!departmentView.value.data || departmentView.value.data.length === 0) {
    return { mileage: [], fuel: [], violations: [], maintenance: [] };
  }
  const data = [...departmentView.value.data];
  const keyMap = {
      mileage: 'total_distance',
      fuel: 'total_fuel',
      violations: 'violation_count',
      maintenance: 'total_maintenance_cost'
  };
  const rankings = {};
  for (const key in keyMap) {
      rankings[key] = [...data].sort((a, b) => (b[keyMap[key]] || 0) - (a[keyMap[key]] || 0));
  }
  return rankings;
});


// (新增) ECharts 图表配置
const chartOption = computed(() => {
    const metric = departmentView.value.activeTab;
    const currentTabInfo = tabs.find(t => t.id === metric);
    if (!metric || !departmentView.value.data.length || !currentTabInfo) {
        return null;
    }

    const sortedData = [...departmentView.value.data].sort((a, b) => {
        const keyMap = {
            mileage: 'total_distance',
            fuel: 'total_fuel',
            violations: 'violation_count',
            maintenance: 'total_maintenance_cost'
        };
        return (b[keyMap[metric]] || 0) - (a[keyMap[metric]] || 0);
    });

    const labels = sortedData.map(d => d.name);
    const data = sortedData.map(d => {
        const keyMap = {
            mileage: 'total_distance',
            fuel: 'total_fuel',
            violations: 'violation_count',
            maintenance: 'total_maintenance_cost'
        };
        return d[keyMap[metric]] || 0;
    });

    // (新增) 动态计算 dataZoom 的结束位置，以优化初始显示
    const initialDisplayCount = 15; // 初始显示的柱子数量
    const endPercentage = labels.length > initialDisplayCount 
        ? (initialDisplayCount / labels.length) * 100 
        : 100;

    return {
        title: {
            text: `各部门${currentTabInfo.name}对比`,
            left: 'center'
        },
        tooltip: {
            trigger: 'axis',
            axisPointer: { type: 'shadow' },
            formatter: (params) => {
                const item = params[0];
                return `${item.name}<br/>${currentTabInfo.label}: ${item.value.toLocaleString()} ${currentTabInfo.unit}`;
            }
        },
        grid: {
            left: '3%',
            right: '4%',
            bottom: '15%', // (修改) 增加底部边距，为 dataZoom 和旋转的标签留出空间
            containLabel: true
        },
        xAxis: {
            type: 'category',
            data: labels,
            axisLabel: {
                interval: 0,
                rotate: 40 // (修改) 增加旋转角度
            }
        },
        yAxis: {
            type: 'value',
            name: currentTabInfo.unit
        },
        series: [{
            name: currentTabInfo.label,
            type: 'bar',
            data: data,
            barWidth: '60%',
            itemStyle: { color: '#3498db' },
            emphasis: { itemStyle: { color: '#2980b9' } }
        }],
        // (新增) dataZoom 配置
        dataZoom: [{
            type: 'slider',
            start: 0,
            end: endPercentage,
            bottom: 30,
            height: 20,
            showDetail: false,
        }]
    };
});


// (新增) 计算属性，用于判断筛选器是否有效
const isFilterValid = computed(() => {
    return filters.value.startMonth && filters.value.endMonth && filters.value.startMonth <= filters.value.endMonth;
});


// (删除) 移除旧的 chart.js 渲染方法
// const renderChart = ...
// const renderDepartmentChart = ...

const fetchData = async () => {
  departmentView.value.isLoading = true;
  departmentView.value.error = null;
  // (修改) 将筛选器和分页参数加入请求
  const params = new URLSearchParams({
    start_month: filters.value.startMonth,
    end_month: filters.value.endMonth,
    page: departmentView.value.pagination.page,
    per_page: departmentView.value.pagination.per_page,
  });
  try {
    const response = await fetch(`http://127.0.0.1:5000/api/department/summary?${params.toString()}`);
    if (!response.ok) throw new Error('Network response was not ok');
    
    // (修改) 处理新的API响应结构
    const responseData = await response.json();
    departmentView.value.data = responseData.departments;
    departmentView.value.kpis = responseData.kpis;
    departmentView.value.pagination = responseData.pagination; // (新增) 更新分页数据

  } catch (e) {
    departmentView.value.error = '无法加载部门数据，请检查后端服务。';
    console.error(e);
  } finally {
    departmentView.value.isLoading = false;
    // (删除) 不再需要 nextTick
  }
};

const changeDepartmentTab = (tabId) => {
  departmentView.value.activeTab = tabId;
  // (删除) 移除 nextTick 和 render 调用
};

// (新增) 应用筛选器的方法
const applyFilters = () => {
    if (isFilterValid.value) {
        departmentView.value.pagination.page = 1; // (新增) 筛选时重置到第一页
        fetchData();
    } else {
        alert('请输入有效的起始和结束月份！');
    }
};

// (新增) 切换页面的方法
const changePage = (page) => {
    if (page > 0 && page <= departmentView.value.pagination.total_pages) {
        departmentView.value.pagination.page = page;
        fetchData();
    }
};


onMounted(fetchData);

</script>

<template>
  <div class="department-view">
    <div v-if="departmentView.isLoading" class="loading-container">
      <div class="spinner"></div>
      <p>正在加载部门数据...</p>
    </div>
    <div v-else-if="departmentView.error" class="error-container">
      <p>{{ departmentView.error }}</p>
    </div>
    <div v-else>
      <!-- (新增) 页面顶部的控制区域，包含筛选器 -->
      <div class="page-controls">
          <section class="filters">
              <label for="start-month">时间范围:</label>
              <input type="month" id="start-month" v-model="filters.startMonth">
              <span class="date-separator">至</span>
              <input type="month" id="end-month" v-model="filters.endMonth">
              <button @click="applyFilters" :disabled="!isFilterValid">查询</button>
          </section>
      </div>

      <!-- (新增) KPI 卡片区域 -->
      <div class="kpi-container" v-if="departmentView.kpis.total_departments > 0">
        <div class="kpi-card">
          <h3>平均每部门车辆数</h3>
          <p>{{ (departmentView.kpis.total_vehicles / departmentView.kpis.total_departments).toFixed(1) }} 辆</p>
        </div>
        <div class="kpi-card">
          <h3>平均每部门里程</h3>
          <p>{{ (departmentView.kpis.total_distance / departmentView.kpis.total_departments).toLocaleString(undefined, {maximumFractionDigits: 0}) }} 公里</p>
        </div>
        <div class="kpi-card">
          <h3>平均每部门油耗</h3>
          <p>{{ (departmentView.kpis.total_fuel / departmentView.kpis.total_departments).toLocaleString(undefined, {maximumFractionDigits: 2}) }} 升</p>
        </div>
        <div class="kpi-card">
          <h3>平均每部门违章</h3>
          <p>{{ (departmentView.kpis.violation_count / departmentView.kpis.total_departments).toLocaleString(undefined, {maximumFractionDigits: 2}) }} 次</p>
        </div>
        <div class="kpi-card">
          <h3>平均每部门维保费用</h3>
          <p>¥ {{ (departmentView.kpis.total_maintenance_cost / departmentView.kpis.total_departments).toLocaleString(undefined, {maximumFractionDigits: 2}) }}</p>
        </div>
      </div>

      <div class="tabs">
        <button v-for="tab in tabs" :key="tab.id" :class="{ active: departmentView.activeTab === tab.id }" @click="changeDepartmentTab(tab.id)">
          {{ tab.name }}
        </button>
      </div>

      <!-- (修改) 恢复 grid 布局，将图表和排名列表并列 -->
      <div class="department-content-grid">
        <section class="chart-container">
          <v-chart v-if="chartOption" class="chart" :option="chartOption" autoresize />
          <div v-else class="chart-placeholder">图表数据加载中...</div>
        </section>

        <!-- (恢复) 排名列表 -->
        <section class="ranking-list">
          <div v-for="tab in tabs" :key="tab.id" v-show="departmentView.activeTab === tab.id">
            <h3>{{ tab.name }}排名</h3>
            <ul>
              <li v-for="(dept, index) in departmentRankings[tab.id]" :key="dept.department_id">
                <span class="rank-index">{{ index + 1 }}</span>
                <span class="rank-name">{{ dept.name }}</span>
                <span class="rank-value">
                  {{ tab.id === 'mileage' ? (dept.total_distance || 0).toLocaleString() + ' 公里' : '' }}
                  {{ tab.id === 'fuel' ? (dept.total_fuel || 0).toFixed(2) + ' 升' : '' }}
                  {{ tab.id === 'violations' ? (dept.violation_count || 0) + ' 次' : '' }}
                  {{ tab.id === 'maintenance' ? '¥ ' + (dept.total_maintenance_cost || 0).toFixed(2) : '' }}
                </span>
              </li>
            </ul>
          </div>
        </section>
      </div>


      <section class="department-list">
        <h2>部门数据总览</h2>
        <table>
          <thead>
            <tr>
              <th>部门名称</th>
              <th>车辆数</th>
              <th>总行驶里程 (公里)</th>
              <th>总油耗 (升)</th>
              <th>总违章 (次)</th>
              <th>总维保费用 (元)</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="dept in departmentView.data" :key="dept.department_id">
              <td>
                  <router-link :to="'/department/' + dept.department_id" class="department-link">
                      {{ dept.name }}
                  </router-link>
              </td>
              <td>{{ dept.vehicle_count }}</td>
              <td>{{ dept.total_distance.toLocaleString() }}</td>
              <td>{{ dept.total_fuel.toFixed(2) }}</td>
              <td>{{ dept.violation_count }}</td>
              <td>{{ dept.total_maintenance_cost.toFixed(2) }}</td>
            </tr>
          </tbody>
        </table>
        <!-- (新增) 分页控件 -->
        <div class="pagination-controls" v-if="departmentView.pagination.total_pages > 1">
            <button @click="changePage(1)" :disabled="departmentView.pagination.page === 1">首页</button>
            <button @click="changePage(departmentView.pagination.page - 1)" :disabled="departmentView.pagination.page === 1">上一页</button>
            <span>第 {{ departmentView.pagination.page }} 页 / 共 {{ departmentView.pagination.total_pages }} 页</span>
            <button @click="changePage(departmentView.pagination.page + 1)" :disabled="departmentView.pagination.page >= departmentView.pagination.total_pages">下一页</button>
            <button @click="changePage(departmentView.pagination.total_pages)" :disabled="departmentView.pagination.page >= departmentView.pagination.total_pages">末页</button>
        </div>
      </section>
    </div>
  </div>
</template>

<style scoped>
/* Scoped styles for the department page */
.department-view h2 {
    font-size: 24px;
    color: #333;
    margin-bottom: 20px;
    border-bottom: 2px solid #3498db;
    padding-bottom: 10px;
}
.department-list table {
    width: 100%;
    border-collapse: collapse;
    margin-top: 15px;
    box-shadow: 0 1px 3px rgba(0,0,0,0.05);
}
.department-list th,
.department-list td {
    padding: 12px 15px;
    text-align: left;
    border-bottom: 1px solid #e0e0e0;
}
.department-list thead tr {
    background-color: #f8f9fa;
}
.department-list th {
    font-weight: 600;
    color: #333;
    font-size: 14px;
}
.department-list tbody tr:hover {
    background-color: #f1f1f1;
}
.department-list td {
    color: #555;
    font-size: 14px;
}

.department-link {
    text-decoration: none;
    color: #3498db;
    font-weight: bold;
}

.department-link:hover {
    text-decoration: underline;
}

/* (新增) 分页控件样式 */
.pagination-controls {
    margin-top: 20px;
    display: flex;
    justify-content: center;
    align-items: center;
    gap: 10px;
}
.pagination-controls button {
    padding: 8px 15px;
    border: 1px solid #ddd;
    background-color: #fff;
    cursor: pointer;
    border-radius: 4px;
}
.pagination-controls button:disabled {
    cursor: not-allowed;
    background-color: #f5f5f5;
    color: #aaa;
}
.pagination-controls span {
    font-size: 14px;
    color: #555;
}

/* (新增) 页面筛选器样式 */
.page-filters {
    display: flex;
    justify-content: flex-end;
    align-items: center;
    gap: 10px;
    margin-bottom: 20px;
}
.page-filters label {
    font-weight: bold;
    color: #333;
    font-size: 14px;
}
.page-filters input[type="month"] {
    padding: 6px 10px;
    border: 1px solid #ccc;
    border-radius: 4px;
}
.page-filters button {
    padding: 6px 18px;
    border: none;
    background-color: #3498db;
    color: white;
    border-radius: 4px;
    cursor: pointer;
}
.page-filters button:disabled {
    background-color: #bdc3c7;
}

/* (新增) 页面顶部控制区域和筛选器样式 */
.page-controls {
    display: flex;
    justify-content: flex-end;
    align-items: center;
    margin-bottom: 20px;
}
.filters {
    display: flex;
    align-items: center;
    gap: 10px;
}
.filters label {
    font-weight: 500;
    color: #333;
    font-size: 14px;
}
.date-separator {
    color: #555;
    font-size: 14px;
}
.filters input[type="month"] {
    padding: 6px 10px;
    border: 1px solid #ccc;
    border-radius: 4px;
    font-size: 14px;
}
.filters button {
    padding: 6px 18px;
    border: none;
    background-color: #3498db;
    color: white;
    font-size: 14px;
    font-weight: bold;
    border-radius: 4px;
    cursor: pointer;
    transition: background-color 0.3s, transform 0.1s;
}
.filters button:hover:not(:disabled) {
    background-color: #2980b9;
    transform: translateY(-1px);
}
.filters button:disabled {
    background-color: #bdc3c7;
    cursor: not-allowed;
}

/* (新增) KPI 卡片样式 */
.kpi-container {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 20px;
  margin-bottom: 20px;
}

.kpi-card {
  background-color: #fff;
  padding: 20px;
  border-radius: 8px;
  box-shadow: 0 2px 10px rgba(0, 0, 0, 0.05);
  text-align: center;
}

.kpi-card h3 {
  margin: 0 0 10px;
  font-size: 16px;
  color: #555;
}

.kpi-card p {
  margin: 0;
  font-size: 24px;
  font-weight: bold;
  color: #3498db;
}


/* (修改) 布局样式 */
.department-content-grid {
    display: grid;
    grid-template-columns: 3fr 1fr;
    gap: 25px;
    margin-bottom: 30px;
}

.chart-container, .ranking-list {
    background-color: #fff;
    padding: 20px;
    border-radius: 8px;
    box-shadow: 0 2px 10px rgba(0, 0, 0, 0.05);
    height: 500px;
}

.ranking-list {
    overflow-y: auto;
}

.ranking-list h3 {
    margin-top: 0;
    font-size: 18px;
    border-bottom: 1px solid #eee;
    padding-bottom: 10px;
    position: sticky;
    top: -20px; /* 配合父容器的padding */
    background: #fff;
    z-index: 1;
}

.ranking-list ul {
    list-style: none;
    padding: 0;
    margin: 0;
}

.ranking-list li {
    display: flex;
    align-items: center;
    padding: 10px 0;
    border-bottom: 1px solid #f0f0f0;
    font-size: 14px;
}

.ranking-list li:last-child {
    border-bottom: none;
}

.rank-index {
    font-weight: bold;
    color: #3498db;
    width: 30px;
    text-align: center;
}

.rank-name {
    flex-grow: 1;
    color: #555;
    padding: 0 10px;
}

.rank-value {
    font-weight: 500;
    color: #333;
}


/* (删除) 移除不再使用的样式 */
.chart-container-fullwidth {
    display: none;
}

.tabs {
    display: flex;
    border-bottom: 1px solid #e0e0e0;
    margin-bottom: 20px;
}
.tabs button {
    flex: 1;
    padding: 15px 10px;
    border: none;
    background-color: transparent;
    font-size: 16px;
    cursor: pointer;
    transition: background-color 0.3s, color 0.3s;
    border-bottom: 3px solid transparent;
    margin-bottom: -1px;
}
.tabs button:hover {
    background-color: #f5f5f5;
}
.tabs button.active {
    font-weight: bold;
    color: #3498db;
    border-bottom-color: #3498db;
}

/* (移除) 趋势图相关样式 */
/*
.trend-chart-container {
    margin-top: 30px;
    margin-bottom: 30px;
    background-color: #fff;
    padding: 20px;
    border-radius: 8px;
    box-shadow: 0 2px 10px rgba(0, 0, 0, 0.05);
}
.chart-wrapper {
    height: 500px;
    position: relative;
}
*/
</style>
