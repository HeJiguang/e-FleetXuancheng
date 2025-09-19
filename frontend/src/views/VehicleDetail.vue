<template>
  <div class="vehicle-detail-view">
    <div v-if="isLoading" class="loading-container">
      <div class="spinner"></div>
      <p>正在加载车辆详细信息...</p>
    </div>
    <div v-else-if="error" class="error-container">
      <p>{{ error }}</p>
    </div>
    <div v-else-if="vehicleData" class="detail-content">
      <!-- 顶部信息栏 -->
      <header class="vehicle-header">
        <div class="vehicle-image">
          <img :src="vehicleData.basic_info.vehicle_image_url" :alt="vehicleData.basic_info.plate_number">
          <!-- (新增) 上传控件 -->
          <div class="upload-overlay" @click="triggerFileUpload">
            <span>点击上传图片</span>
          </div>
          <input type="file" ref="fileInput" @change="handleFileUpload" accept="image/*" style="display: none;" />
        </div>
        <div class="vehicle-kpis">
          <h1>{{ vehicleData.basic_info.plate_number }}</h1>
          <div class="kpi-grid">
            <div class="kpi-item"><span>所属部门</span><strong>{{ vehicleData.basic_info.department_name }}</strong></div>
            <div class="kpi-item"><span>品牌型号</span><strong>{{ vehicleData.basic_info.brand_model }}</strong></div>
            <div class="kpi-item"><span>车管员</span><strong>{{ vehicleData.basic_info.manager }}</strong></div>
            <div class="kpi-item"><span>注册日期</span><strong>{{ vehicleData.basic_info.registration_date }}</strong></div>
            <div class="kpi-item"><span>采购价格</span><strong>¥ {{ (vehicleData.basic_info.purchase_price || 0).toLocaleString() }}</strong></div>
          </div>
        </div>
      </header>

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

      <!-- 主要内容区 -->
      <main class="vehicle-main">
        <!-- 里程管理 -->
        <section class="data-card">
          <h2>里程管理</h2>
          <div class="card-kpis">
            <div class="kpi-card">
              <h3>总行驶里程</h3>
              <p>{{ (vehicleData.mileage.total_distance || 0).toLocaleString() }} <span>公里</span></p>
            </div>
          </div>
          <div class="chart-container">
            <v-chart class="chart" :option="mileageChartOption" autoresize />
          </div>
          <div class="detail-table-container">
            <h3>月度里程明细</h3>
            <table>
              <thead>
                <tr>
                  <th>月份</th>
                  <th>行驶里程 (公里)</th>
                  <th>百公里油耗 (升)</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="item in vehicleData.mileage.details" :key="item.month">
                  <td>{{ item.month }}</td>
                  <td>{{ (item.distance_driven || 0).toLocaleString() }}</td>
                  <td>{{ (item.avg_consumption_per_100km || 0).toFixed(2) }}</td>
                </tr>
              </tbody>
            </table>
          </div>
        </section>
        
        <!-- 油耗管理 -->
        <section class="data-card">
          <h2>油耗管理</h2>
          <div class="card-kpis">
            <div class="kpi-card">
              <h3>总油耗</h3>
              <p>{{ (vehicleData.fuel.total_fuel || 0).toFixed(2) }} <span>升</span></p>
            </div>
            <div class="kpi-card">
              <h3>总油费</h3>
              <p>¥ {{ (vehicleData.fuel.total_fuel_cost || 0).toLocaleString(undefined, { maximumFractionDigits: 2 }) }}</p>
            </div>
             <div class="kpi-card">
              <h3>平均油耗</h3>
              <p>{{ (vehicleData.fuel.avg_consumption || 0).toFixed(2) }} <span>升/百公里</span></p>
            </div>
          </div>
          <div class="chart-container">
            <v-chart class="chart" :option="fuelChartOption" autoresize />
          </div>
        </section>

        <!-- 违章管理 -->
        <section class="data-card">
          <h2>违章管理</h2>
           <div class="card-kpis">
            <div class="kpi-card">
              <h3>总违章次数</h3>
              <p>{{ vehicleData.violations.total_count }} <span>次</span></p>
            </div>
            <div class="kpi-card">
              <h3>部门排名</h3>
              <p>第 {{ vehicleData.violations.rank_info.rank }} <span>/ 共 {{ vehicleData.violations.rank_info.total_vehicles }} 辆</span></p>
            </div>
          </div>
          <div class="chart-container">
            <v-chart class="chart" :option="violationChartOption" autoresize />
          </div>
          <div class="detail-table-container">
            <h3>违章记录明细</h3>
            <table>
              <thead>
                <tr>
                  <th>违章时间</th>
                  <th>违章地点</th>
                  <th>违章原因</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="(item, index) in vehicleData.violations.details" :key="index">
                  <td>{{ item.violation_time }}</td>
                  <td>{{ item.violation_location }}</td>
                  <td>{{ item.violation_reason }}</td>
                </tr>
              </tbody>
            </table>
          </div>
        </section>

        <!-- 维保管理 -->
        <section class="data-card">
          <h2>维保管理</h2>
           <div class="card-kpis">
            <div class="kpi-card">
              <h3>总维保次数</h3>
              <p>{{ vehicleData.maintenance.total_count }} <span>次</span></p>
            </div>
            <div class="kpi-card">
              <h3>总维保费用</h3>
              <p>¥ {{ (vehicleData.maintenance.total_cost || 0).toLocaleString(undefined, { maximumFractionDigits: 2 }) }}</p>
            </div>
            <div class="kpi-card">
              <h3>月均维保费用</h3>
              <p>¥ {{ (vehicleData.maintenance.avg_monthly_cost || 0).toLocaleString(undefined, { maximumFractionDigits: 2 }) }}</p>
            </div>
          </div>
          <div class="detail-table-container">
            <h3>维保记录明细</h3>
             <table>
              <thead>
                <tr>
                  <th>送修时间</th>
                  <th>维保单位</th>
                  <th>维保内容</th>
                  <th>维保费用 (元)</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="(item, index) in vehicleData.maintenance.details" :key="index">
                  <td>{{ item.request_time }}</td>
                  <td>{{ item.provider_name }}</td>
                  <td>{{ item.service_details }}</td>
                  <td>{{ (item.maintenance_cost || 0).toFixed(2) }}</td>
                </tr>
              </tbody>
            </table>
          </div>
        </section>
      </main>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, computed } from 'vue';
import { use } from 'echarts/core';
import { CanvasRenderer } from 'echarts/renderers';
import { BarChart, LineChart } from 'echarts/charts';
import {
  TitleComponent,
  TooltipComponent,
  GridComponent,
  LegendComponent,
} from 'echarts/components';
import VChart from 'vue-echarts';

use([
  CanvasRenderer,
  BarChart,
  LineChart,
  TitleComponent,
  TooltipComponent,
  GridComponent,
  LegendComponent,
]);

const props = defineProps({
  plate_number: {
    type: String,
    required: true,
  },
});

const isLoading = ref(true);
const error = ref(null);
const vehicleData = ref(null);
const fileInput = ref(null);

// (新增) 筛选器状态
const filters = ref({
  startMonth: '2025-01',
  endMonth: '2025-06'
});

const fetchData = async () => {
  isLoading.value = true;
  error.value = null;
  try {
    const encodedPlateNumber = encodeURIComponent(props.plate_number);
    // (新增) 将筛选器参数加入请求
    const params = new URLSearchParams({
        start_month: filters.value.startMonth,
        end_month: filters.value.endMonth
    });
    const response = await fetch(`http://127.0.0.1:5000/api/vehicle/detail/${encodedPlateNumber}?${params.toString()}`);
    if (!response.ok) {
        const errData = await response.json();
        throw new Error(errData.error || 'Failed to fetch vehicle details');
    }
    vehicleData.value = await response.json();
  } catch (e) {
    error.value = e.message;
  } finally {
    isLoading.value = false;
  }
};

// (新增) 触发文件选择
const triggerFileUpload = () => {
    fileInput.value.click();
};

// (新增) 处理文件上传
const handleFileUpload = async (event) => {
    const file = event.target.files[0];
    if (!file) return;

    const formData = new FormData();
    formData.append('file', file);

    try {
        const encodedPlateNumber = encodeURIComponent(props.plate_number);
        const response = await fetch(`http://127.0.0.1:5000/api/vehicle/upload_image/${encodedPlateNumber}`, {
            method: 'POST',
            body: formData,
        });

        if (!response.ok) {
            const errData = await response.json();
            throw new Error(errData.error || 'Upload failed');
        }

        const result = await response.json();
        // (新增) 更新前端显示的图片 URL
        if (vehicleData.value) {
            vehicleData.value.basic_info.vehicle_image_url = result.imageUrl;
        }
        alert('图片上传成功！');

    } catch (e) {
        alert(`上传失败: ${e.message}`);
    } finally {
        // 重置 input 以便可以再次上传同名文件
        if(fileInput.value) fileInput.value.value = '';
    }
};

// (新增) 计算属性，用于判断筛选器是否有效
const isFilterValid = computed(() => {
    return filters.value.startMonth && filters.value.endMonth && filters.value.startMonth <= filters.value.endMonth;
});

// (新增) 应用筛选器的方法
const applyFilters = () => {
    if (isFilterValid.value) {
        fetchData();
    } else {
        alert('请输入有效的起始和结束月份！');
    }
};


onMounted(fetchData);

// --- ECharts Options ---
const baseChartOptions = (title, unit, labels, data) => ({
  title: { text: title, left: 'center', textStyle: { fontSize: 16, fontWeight: 'normal' } },
  tooltip: { trigger: 'axis' },
  grid: { left: '3%', right: '4%', bottom: '3%', containLabel: true },
  xAxis: { type: 'category', data: labels, boundaryGap: false },
  yAxis: { type: 'value', name: unit },
  series: [{
    data: data,
    type: 'line',
    smooth: true,
    areaStyle: {},
    itemStyle: { color: '#3498db' },
  }],
});

const mileageChartOption = computed(() => {
    if (!vehicleData.value) return null;
    const { trend } = vehicleData.value.mileage;
    return baseChartOptions('月度里程趋势', '公里', trend.labels, trend.data);
});

const fuelChartOption = computed(() => {
    if (!vehicleData.value) return null;
    const { trend } = vehicleData.value.fuel;
    return baseChartOptions('月度油耗趋势', '升', trend.labels, trend.data);
});

const violationChartOption = computed(() => {
    if (!vehicleData.value) return null;
    const { trend } = vehicleData.value.violations;
    return {
        ...baseChartOptions('月度违章趋势', '次', trend.labels, trend.data),
        series: [{ ...baseChartOptions('', '', [], []).series[0], type: 'bar' , data: trend.data}]
    };
});

</script>

<style scoped>
.vehicle-detail-view {
  padding: 20px 40px;
}

/* Header */
.vehicle-header {
  display: flex;
  gap: 30px;
  margin-bottom: 30px;
  background: #fff;
  padding: 20px;
  border-radius: 8px;
  box-shadow: 0 2px 10px rgba(0,0,0,0.05);
}
.vehicle-image img {
  width: 300px;
  height: 180px;
  border-radius: 8px;
  object-fit: cover;
}

/* (新增) 上传相关样式 */
.vehicle-image {
    position: relative;
    cursor: pointer;
}
.upload-overlay {
    position: absolute;
    top: 0;
    left: 0;
    width: 100%;
    height: 100%;
    background-color: rgba(0, 0, 0, 0.5);
    color: white;
    display: flex;
    justify-content: center;
    align-items: center;
    border-radius: 8px;
    opacity: 0;
    transition: opacity 0.3s ease;
    font-size: 16px;
}
.vehicle-image:hover .upload-overlay {
    opacity: 1;
}

.vehicle-kpis {
  flex-grow: 1;
}
.vehicle-kpis h1 {
  margin-top: 0;
  margin-bottom: 20px;
  font-size: 32px;
  color: #333;
}
.kpi-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 15px;
}
.kpi-item {
  display: flex;
  flex-direction: column;
}
.kpi-item span {
  font-size: 14px;
  color: #888;
  margin-bottom: 5px;
}
.kpi-item strong {
  font-size: 18px;
  color: #333;
}

/* (新增) 筛选器样式 */
.page-controls {
    display: flex;
    justify-content: flex-end;
    align-items: center;
    margin-bottom: 20px;
    background: #fff;
    padding: 15px 20px;
    border-radius: 8px;
    box-shadow: 0 2px 10px rgba(0,0,0,0.05);
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

/* Main Content */
.vehicle-main {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 25px;
}
.data-card {
  background: #fff;
  padding: 20px;
  border-radius: 8px;
  box-shadow: 0 2px 10px rgba(0,0,0,0.05);
  grid-column: span 1;
}
.data-card h2 {
  margin-top: 0;
  border-bottom: 2px solid #3498db;
  padding-bottom: 10px;
  margin-bottom: 20px;
}
.data-card:nth-child(1), .data-card:nth-child(2) {
    grid-column: span 1;
}
.data-card:nth-child(3), .data-card:nth-child(4) {
    grid-column: span 2;
}


/* Card KPIs */
.card-kpis {
  display: flex;
  gap: 15px;
  margin-bottom: 20px;
}
.kpi-card {
  flex: 1;
  background: #f8f9fa;
  padding: 15px;
  border-radius: 8px;
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

/* Chart */
.chart-container {
  height: 250px;
  margin-bottom: 20px;
}
.chart {
  width: 100%;
  height: 100%;
}

/* Detail Table */
.detail-table-container h3 {
    font-size: 16px;
    margin-bottom: 10px;
}
.detail-table-container table {
  width: 100%;
  border-collapse: collapse;
}
.detail-table-container th,
.detail-table-container td {
  padding: 8px 12px;
  text-align: left;
  border-bottom: 1px solid #e0e0e0;
  font-size: 14px;
}
.detail-table-container thead {
  background-color: #f8f9fa;
}

/* Loading/Error */
.loading-container, .error-container {
  text-align: center;
  padding: 60px;
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
