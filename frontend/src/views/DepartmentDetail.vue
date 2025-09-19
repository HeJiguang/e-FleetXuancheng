<template>
  <div class="department-detail-view">
    <div v-if="isLoading" class="loading-container">
      <div class="spinner"></div>
      <p>正在加载部门详细信息...</p>
    </div>
    <div v-else-if="error" class="error-container">
      <p>{{ error }}</p>
    </div>
    <div v-else-if="pageData" class="detail-content">
      <!-- 顶部信息栏 -->
      <header class="page-header">
        <h1>{{ pageData.department_info.name }} - 部门详细</h1>
        <div class="page-controls">
          <section class="filters">
              <label for="start-month">时间范围:</label>
              <input type="month" id="start-month" v-model="filters.startMonth">
              <span class="date-separator">至</span>
              <input type="month" id="end-month" v-model="filters.endMonth">
              <button @click="applyFilters" :disabled="!isFilterValid">查询</button>
          </section>
        </div>
      </header>
      
      <!-- KPI卡片区 -->
      <section class="kpi-container">
        <div class="kpi-card"><h3>车辆总数</h3><p>{{ pageData.kpis.vehicle_count }} <span>辆</span></p></div>
        <div class="kpi-card"><h3>总行驶里程</h3><p>{{ (pageData.kpis.total_distance || 0).toLocaleString() }} <span>公里</span></p></div>
        <div class="kpi-card"><h3>总油耗</h3><p>{{ (pageData.kpis.total_fuel || 0).toLocaleString(undefined, {maximumFractionDigits: 2}) }} <span>升</span></p></div>
        <div class="kpi-card"><h3>总违章</h3><p>{{ (pageData.kpis.violation_count || 0) }} <span>次</span></p></div>
        <div class="kpi-card"><h3>总维保费用</h3><p>¥ {{ (pageData.kpis.maintenance_cost || 0).toLocaleString(undefined, {maximumFractionDigits: 2}) }}</p></div>
      </section>

      <!-- 主要内容区 -->
      <main class="main-grid">
        <!-- 里程管理 -->
        <section class="data-card">
          <h2>里程管理</h2>
          <div class="chart-container">
             <v-chart class="chart" :option="mileageChartOption" autoresize />
          </div>
          <div class="ranking-container">
            <h4>部门内车辆里程排名</h4>
            <ul>
                <li v-for="(item, index) in pageData.rankings.mileage" :key="item.plate_number">
                    <span>{{ index + 1 }}. {{ item.plate_number }}</span>
                    <strong>{{ (item.value || 0).toLocaleString() }} 公里</strong>
                </li>
            </ul>
          </div>
        </section>
        
        <!-- 油耗管理 -->
        <section class="data-card">
          <h2>油耗管理</h2>
           <div class="chart-container">
             <v-chart class="chart" :option="fuelChartOption" autoresize />
          </div>
        </section>

        <!-- 违章管理 -->
        <section class="data-card">
          <h2>违章管理</h2>
           <div class="chart-container">
             <v-chart class="chart" :option="violationChartOption" autoresize />
          </div>
           <div class="ranking-container">
            <h4>部门内车辆违章排名</h4>
             <ul>
                <li v-for="(item, index) in pageData.rankings.violations" :key="item.plate_number">
                    <span>{{ index + 1 }}. {{ item.plate_number }}</span>
                    <strong>{{ item.value }} 次</strong>
                </li>
            </ul>
          </div>
        </section>

        <!-- 维保管理 -->
        <section class="data-card">
          <h2>维保管理</h2>
          <div class="chart-container">
             <v-chart class="chart" :option="maintenanceChartOption" autoresize />
          </div>
        </section>
        
        <!-- 车辆列表 -->
        <section class="data-card vehicle-list-card">
            <h2>部门车辆列表</h2>
            <table>
              <thead>
                <tr>
                  <th>车牌号</th>
                  <th>品牌型号</th>
                  <th>车管员</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="vehicle in pageData.vehicles" :key="vehicle.vehicle_id">
                  <td>
                     <router-link :to="'/vehicle/' + vehicle.plate_number" class="vehicle-link">
                        {{ vehicle.plate_number }}
                     </router-link>
                  </td>
                  <td>{{ vehicle.brand_model }}</td>
                  <td>{{ vehicle.manager }}</td>
                </tr>
              </tbody>
            </table>
        </section>
      </main>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, computed } from 'vue';
import { RouterLink } from 'vue-router';
import { use } from 'echarts/core';
import { CanvasRenderer } from 'echarts/renderers';
import { BarChart, LineChart } from 'echarts/charts';
import { TitleComponent, TooltipComponent, GridComponent, LegendComponent } from 'echarts/components';
import VChart from 'vue-echarts';

use([CanvasRenderer, BarChart, LineChart, TitleComponent, TooltipComponent, GridComponent, LegendComponent]);

const props = defineProps({
  id: {
    type: [String, Number],
    required: true,
  },
});

const isLoading = ref(true);
const error = ref(null);
const pageData = ref(null);

const filters = ref({
  startMonth: '2025-01',
  endMonth: '2025-06',
});

const isFilterValid = computed(() => filters.value.startMonth && filters.value.endMonth && filters.value.startMonth <= filters.value.endMonth);

const fetchData = async () => {
  isLoading.value = true;
  error.value = null;
  const params = new URLSearchParams({
    start_month: filters.value.startMonth,
    end_month: filters.value.endMonth,
  });
  try {
    const response = await fetch(`http://127.0.0.1:5000/api/department/detail/${props.id}?${params.toString()}`);
    if (!response.ok) {
      const errData = await response.json();
      throw new Error(errData.error || 'Failed to fetch department details');
    }
    pageData.value = await response.json();
  } catch (e) {
    error.value = e.message;
  } finally {
    isLoading.value = false;
  }
};

const applyFilters = () => {
  if (isFilterValid.value) {
    fetchData();
  } else {
    alert('请输入有效的起始和结束月份！');
  }
};

onMounted(fetchData);

// ECharts Options
const baseChartOptions = (title, unit, labels, data, type = 'line') => ({
  title: { text: title, left: 'center', textStyle: { fontSize: 16, fontWeight: 'normal' } },
  tooltip: { trigger: 'axis' },
  grid: { left: '3%', right: '4%', bottom: '3%', containLabel: true },
  xAxis: { type: 'category', data: labels, boundaryGap: type === 'bar' },
  yAxis: { type: 'value', name: unit },
  series: [{
    data: data,
    type: type,
    smooth: type === 'line',
    areaStyle: type === 'line' ? {} : null,
    itemStyle: { color: '#3498db' },
  }],
});

const mileageChartOption = computed(() => pageData.value ? baseChartOptions('月度里程趋势', '公里', pageData.value.trends.mileage.labels, pageData.value.trends.mileage.data) : null);
const fuelChartOption = computed(() => pageData.value ? baseChartOptions('月度油耗趋势', '升', pageData.value.trends.fuel.labels, pageData.value.trends.fuel.data) : null);
const violationChartOption = computed(() => pageData.value ? baseChartOptions('月度违章趋势', '次', pageData.value.trends.violations.labels, pageData.value.trends.violations.data, 'bar') : null);
const maintenanceChartOption = computed(() => pageData.value ? baseChartOptions('月度维保费用趋势', '元', pageData.value.trends.maintenance.labels, pageData.value.trends.maintenance.data) : null);

</script>

<style scoped>
.department-detail-view {
  padding: 20px 40px;
}
.page-header {
  margin-bottom: 20px;
}
.page-header h1 {
  margin-top: 0;
}
.kpi-container {
  display: grid;
  grid-template-columns: repeat(5, 1fr);
  gap: 20px;
  margin-bottom: 30px;
}
.kpi-card {
  background: #fff;
  padding: 20px;
  border-radius: 8px;
  box-shadow: 0 2px 10px rgba(0,0,0,0.05);
  text-align: center;
}
.kpi-card h3 {
  margin: 0 0 10px;
  font-size: 14px;
  color: #555;
  font-weight: 500;
}
.kpi-card p {
  margin: 0;
  font-size: 24px;
  font-weight: bold;
  color: #3498db;
}
.kpi-card p span {
  font-size: 14px;
  font-weight: normal;
  color: #888;
  margin-left: 5px;
}

.main-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 25px;
}
.data-card {
  background: #fff;
  padding: 20px;
  border-radius: 8px;
  box-shadow: 0 2px 10px rgba(0,0,0,0.05);
}
.data-card h2 {
  margin-top: 0;
  border-bottom: 1px solid #eee;
  padding-bottom: 10px;
  margin-bottom: 20px;
}
.chart-container {
  height: 250px;
  margin-bottom: 20px;
}
.chart {
  width: 100%;
  height: 100%;
}
.ranking-container h4 {
    font-size: 14px;
    margin-bottom: 10px;
    color: #333;
}
.ranking-container ul {
    list-style: none;
    padding: 0;
    margin: 0;
    max-height: 150px;
    overflow-y: auto;
}
.ranking-container li {
    display: flex;
    justify-content: space-between;
    padding: 5px 0;
    font-size: 14px;
    border-bottom: 1px solid #f0f0f0;
}
.vehicle-list-card {
    grid-column: span 2;
}
.vehicle-list-card table {
    width: 100%;
    border-collapse: collapse;
}
.vehicle-list-card th, .vehicle-list-card td {
    padding: 8px 12px;
    text-align: left;
    border-bottom: 1px solid #e0e0e0;
    font-size: 14px;
}
.vehicle-link {
    text-decoration: none;
    color: #3498db;
    font-weight: bold;
}
.vehicle-link:hover {
    text-decoration: underline;
}
.page-controls, .filters, .date-separator { /* Reuse styles from other views */
    display: flex;
    align-items: center;
    gap: 10px;
}
.filters label { font-weight: 500; }
.filters input { padding: 6px 10px; border: 1px solid #ccc; border-radius: 4px; }
.filters button { padding: 6px 18px; border: none; background-color: #3498db; color: white; border-radius: 4px; cursor: pointer; }
.filters button:disabled { background-color: #bdc3c7; }
</style>
