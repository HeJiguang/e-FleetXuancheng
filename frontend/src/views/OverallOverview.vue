<script setup>
// (删除) 移除 chart.js
// import Chart from 'chart.js/auto';

// (新增) 导入 ECharts
import { use } from 'echarts/core';
import { CanvasRenderer } from 'echarts/renderers';
import { LineChart, PieChart } from 'echarts/charts'; // (修改) 增加 PieChart
import {
  TitleComponent,
  TooltipComponent,
  GridComponent,
  LegendComponent,
} from 'echarts/components';
import VChart from 'vue-echarts';
import { ref, onMounted, computed } from 'vue';
import { useRouter } from 'vue-router'; // (新增)

// (新增)
const router = useRouter();

// (新增) 注册 ECharts 组件
use([
  CanvasRenderer,
  LineChart,
  PieChart, // (修改) 注册 PieChart
  TitleComponent,
  TooltipComponent,
  GridComponent,
  LegendComponent,
]);


// Reactive state
const overview = ref({
  kpi: {},
  charts: {},
  insight_kpis: {}
});
const isLoading = ref(true);
const error = ref(null);
const activeTab = ref('mileage');
const filters = ref({
  startMonth: '2025-01',
  endMonth: '2025-06'
});

// (删除) 移除 chart.js 实例
// const charts = {}; 

const tabs = [
  { id: 'mileage', name: '里程管理', unit: '公里', trendKey: 'mileage_trend' },
  { id: 'fuel', name: '油耗管理', unit: '升', trendKey: 'fuel_trend' },
  { id: 'violations', name: '违章管理', unit: '次', trendKey: 'violation_trend' },
  { id: 'maintenance', name: '维保管理', unit: '元', trendKey: 'maintenance_trend' }
];

// (新增) ECharts 图表配置
const chartOption = computed(() => {
    const currentTab = tabs.find(t => t.id === activeTab.value);
    if (!currentTab || !overview.value.charts[currentTab.trendKey]) {
        return null;
    }

    const chartData = overview.value.charts[currentTab.trendKey];
    const dualYAxisTab = 'maintenance';
    let series = [];
    let yAxis = [{
        type: 'value',
        name: currentTab.unit,
        axisLabel: { formatter: `{value} ${currentTab.unit}` }
    }];
    let legendData = [currentTab.name];

    if (activeTab.value === dualYAxisTab) {
        const countData = overview.value.charts.maintenance_count_trend;
        legendData.push('维保次数');
        series = [
            {
                name: currentTab.name,
                type: 'line',
                data: chartData.data,
                smooth: true,
                itemStyle: { color: '#3498db' }
            },
            {
                name: '维保次数',
                type: 'line',
                yAxisIndex: 1,
                data: countData.data,
                smooth: true,
                itemStyle: { color: '#e74c3c' }
            }
        ];
        yAxis.push({
            type: 'value',
            name: '次',
            axisLabel: { formatter: '{value} 次' }
        });
    } else {
        series = [{
            name: currentTab.name,
            type: 'line',
            data: chartData.data,
            smooth: true,
            itemStyle: { color: '#3498db' }
        }];
    }

    return {
        title: {
            text: `月度${currentTab.name}趋势`,
            left: 'center'
        },
        tooltip: {
            trigger: 'axis'
        },
        legend: {
            data: legendData,
            bottom: 10
        },
        grid: {
            left: '3%',
            right: '4%',
            bottom: '15%',
            containLabel: true
        },
        xAxis: {
            type: 'category',
            boundaryGap: false,
            data: chartData.labels
        },
        yAxis: yAxis,
        series: series
    };
});

// (新增) 部门车辆分布图表配置
const distributionChartOption = computed(() => {
    if (!overview.value.charts || !overview.value.charts.vehicles_per_department) {
        return null;
    }
    
    const chartData = overview.value.charts.vehicles_per_department;
    const dataForPie = chartData.labels.map((label, index) => ({
        name: label,
        value: chartData.data[index],
        department_id: chartData.department_ids[index] // (新增)
    }));

    return {
        title: {
            text: '各部门车辆数分布',
            left: 'center',
        },
        tooltip: {
            trigger: 'item',
            formatter: '{b}: {c} 辆 ({d}%)'
        },
        legend: {
            orient: 'vertical',
            left: 'left',
            top: 'middle',
            data: chartData.labels,
            type: 'scroll'
        },
        series: [
            {
                name: '车辆分布',
                type: 'pie',
                radius: ['40%', '70%'],
                center: ['65%', '50%'],
                avoidLabelOverlap: false,
                label: {
                    show: false,
                    position: 'center'
                },
                emphasis: {
                    label: {
                        show: true,
                        fontSize: '20',
                        fontWeight: 'bold'
                    }
                },
                labelLine: {
                    show: false
                },
                data: dataForPie
            }
        ]
    };
});


const fetchData = async () => {
  isLoading.value = true;
  error.value = null;
  const params = new URLSearchParams({
    start_month: filters.value.startMonth,
    end_month: filters.value.endMonth
  });
  try {
    const response = await fetch(`http://127.0.0.1:5000/api/overview/summary?${params.toString()}`);
    if (!response.ok) throw new Error('Network response was not ok');
    overview.value = await response.json();
  } catch (e) {
    error.value = '无法加载概览数据，请检查后端服务。';
    console.error(e);
  } finally {
    isLoading.value = false;
  }
};

const changeTab = (tabId) => {
  activeTab.value = tabId;
};

const applyFilters = () => {
  if (filters.value.startMonth && filters.value.endMonth && filters.value.startMonth <= filters.value.endMonth) {
    fetchData();
  } else {
    alert('请输入有效的起始和结束月份！');
  }
};

// (新增)
const handlePieChartClick = (params) => {
  const departmentId = params.data.department_id;
  if (departmentId) {
    router.push(`/department/${departmentId}`);
  }
};

onMounted(fetchData);

</script>

<template>
  <div>
    <div v-if="isLoading" class="loading-container">
      <div class="spinner"></div>
      <p>正在加载概览数据...</p>
    </div>
    <div v-else-if="error" class="error-container">
      <p>{{ error }}</p>
    </div>
    <div v-else class="overview-container">
      
       <!-- (新增) 顶部全局KPI和分布图 -->
      <section class="global-summary">
        <div class="global-kpi-cards">
            <div class="card">
              <h2>车辆总数</h2>
              <p>{{ overview.kpi.total_vehicles }}</p>
            </div>
            <div class="card">
              <h2>部门总数</h2>
              <p>{{ overview.kpi.total_departments }}</p>
            </div>
        </div>
        <div class="distribution-chart-container">
            <v-chart v-if="distributionChartOption" class="chart" :option="distributionChartOption" autoresize @click="handlePieChartClick" />
            <div v-else class="chart-placeholder">分布数据加载中...</div>
        </div>
      </section>

      <!-- (修改) 页面顶层增加一个筛选器容器 -->
      <section class="page-controls">
        <div class="filters">
          <label for="start-month">时间范围:</label>
          <input type="month" id="start-month" v-model="filters.startMonth">
          <span class="date-separator">至</span>
          <input type="month" id="end-month" v-model="filters.endMonth">
          <button @click="applyFilters" :disabled="!(filters.startMonth && filters.endMonth && filters.startMonth <= filters.endMonth)">查询</button>
        </div>
      </section>

      <section class="management-views">
        <div class="tabs">
          <button v-for="tab in tabs" :key="tab.id" :class="{ active: activeTab === tab.id }" @click="changeTab(tab.id)">
            {{ tab.name }}
          </button>
        </div>

        <!-- (新增) KPI 和 洞察区域 -->
        <div class="kpi-and-insights">
          <div class="kpi-grid">
            <div class="kpi-card" v-if="activeTab === 'mileage'">
              <h3>总行驶里程</h3>
              <p>{{ (overview.kpi.total_distance || 0).toLocaleString() }} 公里</p>
            </div>
             <div class="kpi-card" v-if="activeTab === 'mileage' && overview.kpi.total_vehicles > 0">
              <h3>平均每车里程</h3>
              <p>{{ (overview.kpi.total_distance / overview.kpi.total_vehicles).toLocaleString(undefined, {maximumFractionDigits: 0}) }} 公里</p>
            </div>
            
            <div class="kpi-card" v-if="activeTab === 'fuel'">
              <h3>总油耗</h3>
              <p>{{ (overview.kpi.total_fuel || 0).toLocaleString(undefined, {maximumFractionDigits: 2}) }} 升</p>
            </div>
            <div class="kpi-card" v-if="activeTab === 'fuel'">
              <h3>总加油花费</h3>
              <p>¥ {{ (overview.kpi.total_fuel_cost || 0).toLocaleString(undefined, {maximumFractionDigits: 2}) }}</p>
            </div>
            <div class="kpi-card" v-if="activeTab === 'fuel' && overview.kpi.total_distance > 0">
              <h3>平均百公里油耗</h3>
              <p>{{ (overview.kpi.total_fuel / overview.kpi.total_distance * 100).toLocaleString(undefined, {maximumFractionDigits: 2}) }} 升</p>
            </div>
            
            <div class="kpi-card" v-if="activeTab === 'violations'">
              <h3>总违章次数</h3>
              <p>{{ (overview.kpi.total_violations || 0).toLocaleString() }} 次</p>
            </div>
            <div class="kpi-card" v-if="activeTab === 'violations' && overview.kpi.total_vehicles > 0">
              <h3>平均每车违章</h3>
              <p>{{ (overview.kpi.total_violations / overview.kpi.total_vehicles).toLocaleString(undefined, {maximumFractionDigits: 2}) }} 次</p>
            </div>
            
            <div class="kpi-card" v-if="activeTab === 'maintenance'">
              <h3>总维保次数</h3>
              <p>{{ (overview.kpi.total_maintenance_count || 0).toLocaleString() }} 次</p>
            </div>
            <div class="kpi-card" v-if="activeTab === 'maintenance'">
              <h3>总维保花费</h3>
              <p>¥ {{ (overview.kpi.total_maintenance_cost || 0).toLocaleString(undefined, {maximumFractionDigits: 2}) }}</p>
            </div>
          </div>
          <div class="insights-grid">
            <div class="insight-card" v-if="activeTab === 'violations' && overview.insight_kpis.top_violation_location">
              <h4>最高频违章路段</h4>
              <p>{{ overview.insight_kpis.top_violation_location.violation_location }}</p>
              <span>{{ overview.insight_kpis.top_violation_location.count }} 次</span>
            </div>
            <div class="insight-card" v-if="activeTab === 'violations' && overview.insight_kpis.top_violation_reason">
              <h4>最高频违章原因</h4>
              <p>{{ overview.insight_kpis.top_violation_reason.description }}</p>
              <span>{{ overview.insight_kpis.top_violation_reason.count }} 次</span>
            </div>
            <div class="insight-card" v-if="activeTab === 'maintenance' && overview.insight_kpis.top_maintenance_provider">
              <h4>最常用维保单位</h4>
              <p>{{ overview.insight_kpis.top_maintenance_provider.name }}</p>
              <span>{{ overview.insight_kpis.top_maintenance_provider.count }} 次</span>
            </div>
          </div>
        </div>


        <div class="tab-content">
           <div class="chart-container">
              <v-chart v-if="chartOption" class="chart" :option="chartOption" autoresize />
              <div v-else class="chart-placeholder">图表数据加载中...</div>
            </div>
        </div>
      </section>
    </div>
  </div>
</template>

<style scoped>
/* (删除) 移除所有旧样式 */

/* (新增) 全局加载和错误样式 */
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

/* (新增) 页面主容器 */
.overview-container {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

/* (新增) 页面顶部控制区 */
.page-controls {
  display: flex;
  justify-content: flex-end;
  padding: 10px;
  background-color: #fff;
  border-radius: 8px;
  box-shadow: 0 2px 10px rgba(0, 0, 0, 0.05);
}

.filters {
  display: flex;
  align-items: center;
  gap: 10px;
}

.filters label {
  font-weight: 500;
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
    transition: background-color 0.3s;
}
.filters button:hover:not(:disabled) {
    background-color: #2980b9;
}
.filters button:disabled {
    background-color: #bdc3c7;
    cursor: not-allowed;
}


/* (新增) 管理视图主容器 */
.management-views {
    background-color: #fff;
    border-radius: 8px;
    padding: 20px;
    box-shadow: 0 2px 10px rgba(0, 0, 0, 0.05);
}

/* (新增) 标签页样式 */
.tabs {
    display: flex;
    border-bottom: 1px solid #e0e0e0;
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

/* (新增) KPI 和 洞察区域布局 */
.kpi-and-insights {
  display: grid;
  grid-template-columns: 2fr 1fr;
  gap: 20px;
  padding: 20px 0;
}

.kpi-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
  gap: 15px;
}

.kpi-card, .insight-card {
  background-color: #f8f9fa;
  padding: 15px;
  border-radius: 8px;
  text-align: center;
}

/* (新增) 全局KPI卡片和分布图样式 */
.global-summary {
  display: grid;
  grid-template-columns: 1fr 1fr 2fr; /* (修改) 调整为三列布局 */
  gap: 20px;
  margin-bottom: 20px;
}
.global-kpi-cards {
  display: flex;
  flex-direction: column;
  gap: 20px;
  /* (新增) 让 kpi 卡片占据前两列 */
  grid-column: span 2;
  display: grid;
  grid-template-columns: 1fr 1fr;
}
.global-kpi-cards .card {
    background-color: #fff;
    padding: 20px;
    border-radius: 8px;
    text-align: center;
    box-shadow: 0 2px 10px rgba(0,0,0,0.05);
    border-left: 5px solid #3498db;
}
.global-kpi-cards .card h2 {
    margin: 0 0 10px 0;
    font-size: 18px;
    color: #555;
}
.global-kpi-cards .card p {
    margin: 0;
    font-size: 36px;
    font-weight: bold;
    color: #2c3e50;
}
.distribution-chart-container {
    background-color: #fff;
    padding: 20px;
    border-radius: 8px;
    box-shadow: 0 2px 10px rgba(0,0,0,0.05);
    height: 220px; /* 根据需要调整高度 */
    /* (新增) 让图表占据最后一列 */
    grid-column: 3 / 4;
}
.distribution-chart-container .chart {
    cursor: pointer;
}


.kpi-card h3, .insight-card h4 {
  margin: 0 0 10px;
  font-size: 14px;
  color: #555;
  font-weight: 500;
}

.kpi-card p {
  margin: 0;
  font-size: 22px;
  font-weight: bold;
  color: #3498db;
}

.insights-grid {
  display: flex;
  flex-direction: column;
  gap: 15px;
}

.insight-card {
  border-left: 4px solid #2ecc71;
  text-align: left;
  padding: 10px 15px;
}
.insight-card p {
  margin: 0;
  font-size: 16px;
  font-weight: bold;
  color: #333;
}
.insight-card span {
  font-size: 12px;
  color: #888;
}


/* (新增) 图表区域 */
.tab-content {
    padding-top: 10px;
}
.chart-container {
    height: 400px;
}
.chart, .chart-placeholder {
    width: 100%;
    height: 100%;
}
.chart-placeholder {
    display: flex;
    justify-content: center;
    align-items: center;
    color: #888;
}
</style>
