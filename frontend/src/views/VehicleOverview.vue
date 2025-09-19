<script setup>
import { RouterLink } from 'vue-router'; // (新增)

// (删除) 移除 chart.js 相关的导入
// import Chart from 'chart.js/auto'; 

// (新增) 导入 ECharts 和 vue-echarts 相关模块
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


// 响应式状态 (保持不变)
const vehicleView = ref({
  isLoading: true,
  error: null,
  data: [],
  activeTab: 'mileage',
  pagination: {
    current_page: 1,
    per_page: 10,
    total: 0,
    total_pages: 0
  },
  chart_data: {},
  kpis: {} // (新增) 用于存储 KPI 数据
});

// 筛选器状态 (保持不变)
const filters = ref({
  startMonth: '2025-01',
  endMonth: '2025-06',
  sortBy: 'mileage',
  sortOrder: 'desc',
  page: 1
});

// 标签定义 (保持不变)
const tabs = [
  { id: 'mileage', name: '里程管理', unit: '公里', label: '里程' },
  { id: 'fuel', name: '油耗管理', unit: '升', label: '油耗' },
  { id: 'violations', name: '违章管理', unit: '次', label: '违章次数' },
  { id: 'maintenance', name: '维保管理', unit: '元', label: '维保费用' }
];

// (新增) ECharts 图表配置
const chartOption = computed(() => {
  const metric = vehicleView.value.activeTab;
  const currentTabInfo = tabs.find(t => t.id === metric);
  if (!metric || !vehicleView.value.chart_data[metric] || !currentTabInfo) {
    return null;
  }

  const chartData = vehicleView.value.chart_data[metric];

  // (新增) 动态计算 dataZoom 的结束位置
  const initialDisplayCount = 20; // 初始显示的车辆数量
  const endPercentage = chartData.labels.length > initialDisplayCount 
      ? (initialDisplayCount / chartData.labels.length) * 100 
      : 100;

  return {
    title: {
      text: `车辆${currentTabInfo.label}排名`, // (修改) 移除 "Top 10"
      left: 'center',
      textStyle: {
        color: '#333',
        fontSize: 18,
        fontWeight: 'bold'
      }
    },
    tooltip: {
      trigger: 'axis',
      axisPointer: {
        type: 'shadow'
      },
      formatter: (params) => {
        const dataIndex = params[0].dataIndex;
        const plateNumber = chartData.labels[dataIndex];
        const department = chartData.departments[dataIndex];
        const value = params[0].value;
        return `<b>${plateNumber} (${department})</b><br/>${currentTabInfo.label}: ${value.toLocaleString()} ${currentTabInfo.unit}`;
      }
    },
    grid: {
      left: '3%',
      right: '4%',
      bottom: '15%', // (修改) 增加底部边距
      containLabel: true
    },
    xAxis: {
      type: 'category', // (修改) x轴为类目轴
      data: chartData.labels,
      axisLabel: {
         interval: 0,
         rotate: 40 // (新增) 旋转标签
      }
    },
    yAxis: {
      type: 'value', // (修改) y轴为数值轴
      name: currentTabInfo.unit,
    },
    series: [
      {
        name: `${currentTabInfo.label}排名`, // (修改) 移除 "Top 10"
        type: 'bar',
        data: chartData.data, // (修改) 无需反转
        barWidth: '60%',
        itemStyle: {
            color: '#3498db'
        },
        emphasis: {
            itemStyle: {
                color: '#2980b9'
            }
        }
      }
    ],
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


// 筛选器是否有效 (保持不变)
const isFilterValid = computed(() => {
  return filters.value.startMonth && filters.value.endMonth && filters.value.startMonth <= filters.value.endMonth;
});


// (删除) 移除 chart.js 相关的图表实例和渲染方法
// const charts = {};
// const renderChart = ...
// const renderVehicleChart = ...


// 获取数据
const fetchData = async () => {
  vehicleView.value.isLoading = true;
  vehicleView.value.error = null;
  
  // 构建请求参数
  const params = new URLSearchParams({
    start_month: filters.value.startMonth,
    end_month: filters.value.endMonth,
    sort_by: filters.value.sortBy,
    sort_order: filters.value.sortOrder,
    page: filters.value.page,
    per_page: vehicleView.value.pagination.per_page
  });
  
  try {
    const response = await fetch(`http://127.0.0.1:5000/api/vehicle/summary?${params.toString()}`);
    if (!response.ok) throw new Error('Network response was not ok');
    
    const data = await response.json();
    vehicleView.value.data = data.vehicles;
    vehicleView.value.pagination = data.pagination;
    vehicleView.value.chart_data = data.chart_data;
    vehicleView.value.kpis = data.kpis; // (新增) 保存 KPI 数据
    
  } catch (e) {
    vehicleView.value.error = '无法加载车辆数据，请检查后端服务。';
    console.error(e);
  } finally {
    vehicleView.value.isLoading = false;
    // (删除) 不再需要手动调用渲染图表
    // nextTick(() => {
    //   renderVehicleChart();
    // });
  }
};

// 切换标签页 (保持不变)
const changeVehicleTab = (tabId) => {
  vehicleView.value.activeTab = tabId;
  // 切换标签页时也需要更新排序方式
  filters.value.sortBy = tabId;
  filters.value.sortOrder = 'desc'; // (新增) 默认降序
  fetchData();
};

// 应用筛选器 (保持不变)
const applyFilters = () => {
  if (isFilterValid.value) {
    // 重置到第一页
    filters.value.page = 1;
    fetchData();
  } else {
    alert('请输入有效的起始和结束月份！');
  }
};

// 切换页码 (保持不变)
const changePage = (page) => {
  filters.value.page = page;
  fetchData();
};

// (新增) 切换排序
const changeSort = (column) => {
  if (filters.value.sortBy === column) {
    // 如果是当前排序列，则切换排序方向
    filters.value.sortOrder = filters.value.sortOrder === 'desc' ? 'asc' : 'desc';
  } else {
    // 否则，切换到新的排序列，并默认降序
    filters.value.sortBy = column;
    filters.value.sortOrder = 'desc';
  }
  fetchData();
};


// 组件加载时获取数据 (保持不变)
onMounted(fetchData);
</script>

<template>
  <div class="vehicle-view">
    <div v-if="vehicleView.isLoading" class="loading-container">
      <div class="spinner"></div>
      <p>正在加载车辆数据...</p>
    </div>
    <div v-else-if="vehicleView.error" class="error-container">
      <p>{{ vehicleView.error }}</p>
    </div>
    <div v-else>
      <!-- 页面顶部的控制区域，包含筛选器 -->
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
      <div class="kpi-container">
        <div class="kpi-card" v-if="vehicleView.activeTab === 'mileage'">
          <h3>总行驶里程</h3>
          <p>{{ (vehicleView.kpis.total_distance || 0).toLocaleString() }} 公里</p>
        </div>
        <div class="kpi-card" v-if="vehicleView.activeTab === 'mileage' && vehicleView.pagination.total > 0">
          <h3>平均每车里程</h3>
          <p>{{ (vehicleView.kpis.total_distance / vehicleView.pagination.total).toLocaleString(undefined, { maximumFractionDigits: 0 }) }} 公里</p>
        </div>

        <div class="kpi-card" v-if="vehicleView.activeTab === 'fuel'">
          <h3>总油耗</h3>
          <p>{{ (vehicleView.kpis.total_fuel || 0).toLocaleString(undefined, { maximumFractionDigits: 2 }) }} 升</p>
        </div>
        <div class="kpi-card" v-if="vehicleView.activeTab === 'fuel' && vehicleView.kpis.total_distance > 0">
            <h3>平均百公里油耗</h3>
            <p>{{ (vehicleView.kpis.total_fuel / vehicleView.kpis.total_distance * 100).toLocaleString(undefined, { maximumFractionDigits: 2 }) }} 升</p>
        </div>

        <div class="kpi-card" v-if="vehicleView.activeTab === 'violations'">
          <h3>总违章</h3>
          <p>{{ (vehicleView.kpis.violation_count || 0).toLocaleString() }} 次</p>
        </div>
        <div class="kpi-card" v-if="vehicleView.activeTab === 'violations' && vehicleView.pagination.total > 0">
          <h3>平均每车违章</h3>
          <p>{{ (vehicleView.kpis.violation_count / vehicleView.pagination.total).toLocaleString(undefined, { maximumFractionDigits: 2 }) }} 次</p>
        </div>

        <div class="kpi-card" v-if="vehicleView.activeTab === 'maintenance'">
          <h3>总维保费用</h3>
          <p>¥ {{ (vehicleView.kpis.total_maintenance_cost || 0).toLocaleString(undefined, { maximumFractionDigits: 2 }) }}</p>
        </div>
        <div class="kpi-card" v-if="vehicleView.activeTab === 'maintenance' && vehicleView.pagination.total > 0">
          <h3>平均每车维保</h3>
          <p>¥ {{ (vehicleView.kpis.total_maintenance_cost / vehicleView.pagination.total).toLocaleString(undefined, { maximumFractionDigits: 2 }) }}</p>
        </div>
      </div>


      <div class="tabs">
        <button 
          v-for="tab in tabs" 
          :key="tab.id" 
          :class="{ active: vehicleView.activeTab === tab.id }" 
          @click="changeVehicleTab(tab.id)"
        >
          {{ tab.name }}
        </button>
      </div>

      <!-- 图表区域 (修改) -->
      <div class="chart-container">
         <v-chart v-if="chartOption" class="chart" :option="chartOption" autoresize />
         <div v-else class="chart-placeholder">图表数据加载中...</div>
      </div>


      <!-- 车辆列表区域 -->
      <section class="vehicle-list">
        <h2>车辆数据列表</h2>
        <table>
          <thead>
            <tr>
              <th>车牌号</th>
              <th>所属部门</th>
              <th>购买日期</th>
              <th @click="changeSort('mileage')" class="sortable">
                总行驶里程 (公里)
                <span v-if="filters.sortBy === 'mileage'">{{ filters.sortOrder === 'desc' ? '▼' : '▲' }}</span>
              </th>
              <th @click="changeSort('fuel')" class="sortable">
                总油耗 (升)
                <span v-if="filters.sortBy === 'fuel'">{{ filters.sortOrder === 'desc' ? '▼' : '▲' }}</span>
              </th>
              <th @click="changeSort('violations')" class="sortable">
                总违章 (次)
                <span v-if="filters.sortBy === 'violations'">{{ filters.sortOrder === 'desc' ? '▼' : '▲' }}</span>
              </th>
              <th @click="changeSort('maintenance')" class="sortable">
                总维保费用 (元)
                <span v-if="filters.sortBy === 'maintenance'">{{ filters.sortOrder === 'desc' ? '▼' : '▲' }}</span>
              </th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="vehicle in vehicleView.data" :key="vehicle.vehicle_id" class="vehicle-row">
              <td>
                <router-link :to="'/vehicle/' + vehicle.plate_number" class="vehicle-link">
                  {{ vehicle.plate_number }}
                </router-link>
              </td>
              <td>{{ vehicle.department_name }}</td>
              <td>{{ vehicle.purchase_date }}</td>
              <td>{{ (vehicle.total_distance || 0).toLocaleString() }}</td>
              <td>{{ (vehicle.total_fuel || 0).toFixed(2) }}</td>
              <td>{{ vehicle.violation_count || 0 }}</td>
              <td>{{ (vehicle.total_maintenance_cost || 0).toFixed(2) }}</td>
            </tr>
          </tbody>
        </table>
        
        <!-- 分页控制 -->
        <div class="pagination">
          <button 
            @click="changePage(1)" 
            :disabled="vehicleView.pagination.current_page === 1"
          >首页</button>
          
          <button 
            @click="changePage(vehicleView.pagination.current_page - 1)" 
            :disabled="vehicleView.pagination.current_page === 1"
          >上一页</button>
          
          <span class="page-info">
            {{ vehicleView.pagination.current_page }} / {{ vehicleView.pagination.total_pages }}
            (共 {{ vehicleView.pagination.total }} 条记录)
          </span>
          
          <button 
            @click="changePage(vehicleView.pagination.current_page + 1)" 
            :disabled="vehicleView.pagination.current_page >= vehicleView.pagination.total_pages"
          >下一页</button>
          
          <button 
            @click="changePage(vehicleView.pagination.total_pages)" 
            :disabled="vehicleView.pagination.current_page >= vehicleView.pagination.total_pages"
          >末页</button>
        </div>
      </section>
    </div>
  </div>
</template>

<style scoped>
/* 页面顶部控制区域和筛选器样式 */
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


/* 标签页样式 */
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

/* 图表容器样式 */
.chart-container {
  height: 450px; /* (修改) 调整高度 */
  background-color: #fff;
  padding: 20px;
  border-radius: 8px;
  box-shadow: 0 2px 10px rgba(0, 0, 0, 0.05);
  margin-bottom: 30px;
}

/* (新增) ECharts 图表和占位符样式 */
.chart {
  width: 100%;
  height: 100%;
}
.chart-placeholder {
  display: flex;
  justify-content: center;
  align-items: center;
  height: 100%;
  color: #888;
}


/* 车辆列表样式 */
.vehicle-list h2 {
  font-size: 24px;
  color: #333;
  margin-bottom: 20px;
  border-bottom: 2px solid #3498db;
  padding-bottom: 10px;
}

.vehicle-list table {
  width: 100%;
  border-collapse: collapse;
  margin-top: 15px;
  box-shadow: 0 1px 3px rgba(0,0,0,0.05);
}

.vehicle-list th,
.vehicle-list td {
  padding: 12px 15px;
  text-align: left;
  border-bottom: 1px solid #e0e0e0;
}

/* (新增) 可排序表头样式 */
.vehicle-list th.sortable {
  cursor: pointer;
  user-select: none;
}
.vehicle-list th.sortable:hover {
  background-color: #f0f0f0;
}
.vehicle-list th.sortable span {
  margin-left: 5px;
  color: #3498db;
}


.vehicle-list thead tr {
  background-color: #f8f9fa;
}

.vehicle-list th {
  font-weight: 600;
  color: #333;
  font-size: 14px;
}

.vehicle-list tbody tr:hover {
  background-color: #f1f1f1;
}

/* (新增) 使整行都可以点击 */
.vehicle-row {
    cursor: pointer;
}

.vehicle-link {
    text-decoration: none;
    color: #3498db;
    font-weight: bold;
}

.vehicle-link:hover {
    text-decoration: underline;
}

.vehicle-list td {
  color: #555;
  font-size: 14px;
}

/* 分页控制样式 */
.pagination {
  display: flex;
  justify-content: center;
  align-items: center;
  margin-top: 20px;
  gap: 10px;
}

.pagination button {
  padding: 8px 12px;
  background-color: #f8f9fa;
  border: 1px solid #ddd;
  border-radius: 4px;
  cursor: pointer;
  color: #333;
  font-size: 14px;
}

.pagination button:hover:not(:disabled) {
  background-color: #e9ecef;
}

.pagination button:disabled {
  color: #aaa;
  background-color: #f8f9fa;
  cursor: not-allowed;
}

.page-info {
  padding: 0 15px;
  color: #555;
  font-size: 14px;
}

/* 加载和错误提示样式 */
.loading-container, .error-container {
  text-align: center;
  padding: 40px;
  color: #888;
}

.spinner {
  border: 4px solid #f3f3f3;
  border-top: 4px solid #3498db;
  border-radius: 50%;
  width: 40px;
  height: 40px;
  animation: spin 1s linear infinite;
  margin: 0 auto 10px;
}

@keyframes spin {
  0% { transform: rotate(0deg); }
  100% { transform: rotate(360deg); }
}
</style>
