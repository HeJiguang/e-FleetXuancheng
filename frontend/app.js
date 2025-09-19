// 从 Vue 全局对象中解构出 createApp 方法，这是 Vue 3 的标准用法
const { createApp } = Vue;

// 创建一个新的 Vue 应用实例
createApp({
    // data 方法返回一个对象，这个对象包含了我们应用中所有需要“响应式”的数据
    // “响应式”意味着当这些数据变化时，页面上用到它们的地方会自动更新
    data() {
        return {
            pageTitle: '宣城车e管', // (修改) 页面标题
            currentView: 'overview', // (新增) 控制当前显示的视图: 'overview' 或 'department'
            summary: {
                kpi: { total_vehicles: 0, total_departments: 0 },
                charts: {}
            },
            isLoading: true,
            error: null,
            charts: {},
            // (新增) 定义标签页数据和当前激活的标签页
            activeTab: 'mileage', // 默认显示里程管理
            tabs: [
                { id: 'mileage', name: '里程管理' },
                { id: 'fuel', name: '油耗管理' },
                { id: 'violations', name: '违章管理' },
                { id: 'maintenance', name: '维保管理' }
            ],
            // (新增) 筛选器的数据状态
            filters: {
                startMonth: '2025-01', // 默认起始月份
                endMonth: '2025-06'   // 默认结束月份
            }
        }
    },
    // (新增) 计算属性，用于判断筛选条件是否有效
    computed: {
        isFilterValid() {
            // 确保起始和结束月份都已选择，并且起始不晚于结束
            return this.filters.startMonth && this.filters.endMonth && this.filters.startMonth <= this.filters.endMonth;
        }
    },
    // mounted 是一个“生命周期钩子”，Vue 会在组件被挂载到页面上之后自动执行这个函数
    // 这是发起网络请求获取初始数据的最佳位置
    mounted() {
        // 组件挂载后，开始获取初始化数据
        this.a_fetchSummaryData();
    },
    // methods 对象用于定义可以在应用中调用的方法
    methods: {
        // (修改) 增强导航方法，确保切换视图后能正确重新渲染
        navigateTo(view) {
            // 如果点击的是当前已激活的视图，则不执行任何操作
            if (this.currentView === view) return;

            this.currentView = view;

            // 核心修复：当切换回概览视图时，必须重新调用数据获取和渲染流程，
            // 因为 v-if 已经销毁并重建了 canvas 元素。
            if (view === 'overview') {
                this.a_fetchSummaryData();
            } 
            // else if (view === 'department') {
            //     // 未来，当我们开始构建部门页面时，会在这里调用部门数据的获取方法
            //     // this.a_fetchDepartmentData();
            // }
        },

        // (修改) 调整了渲染时机，修复初始化时图表不显示的Bug
        async a_fetchSummaryData() {
            this.isLoading = true;
            this.error = null;

            const params = new URLSearchParams({
                start_month: this.filters.startMonth,
                end_month: this.filters.endMonth
            });
            const url = `http://127.0.0.1:5000/api/overview/summary?${params.toString()}`;

            try {
                const response = await fetch(url);
                if (!response.ok) {
                    throw new Error(`网络响应错误: ${response.statusText}`);
                }
                this.summary = await response.json();
            } catch (err) {
                console.error('获取概览数据失败:', err);
                this.error = '无法加载概览数据，请检查后端服务。';
            } finally {
                this.isLoading = false;
                // 关键修复: 确保在 isLoading 状态更新、DOM渲染完成后再执行图表绘制
                this.$nextTick(() => {
                    this.renderActiveTabChart();
                });
            }
        },

        // (新增) 应用筛选器的方法
        applyFilters() {
            if (this.isFilterValid) {
                this.a_fetchSummaryData();
            } else {
                alert('请输入有效的起始和结束月份！');
            }
        },

        // (新增) 切换标签页的方法
        changeTab(tabId) {
            this.activeTab = tabId;
            // 切换标签页时，v-if 会导致DOM更新，所以同样需要 nextTick
            this.$nextTick(() => {
                this.renderActiveTabChart();
            });
        },

        // (新增) 动态渲染当前激活标签页的图表
        renderActiveTabChart() {
            switch (this.activeTab) {
                case 'mileage':
                    this.renderTrendChart('mileageTrendChart', this.summary.charts.mileage_trend, '总里程 (公里)', 'rgba(255, 99, 132, 0.6)');
                    break;
                case 'fuel':
                    this.renderTrendChart('fuelTrendChart', this.summary.charts.fuel_trend, '总油耗 (升)', 'rgba(75, 192, 192, 0.6)');
                    break;
                case 'violations':
                     this.renderTrendChart('violationTrendChart', this.summary.charts.violation_trend, '违章次数', 'rgba(255, 206, 86, 0.6)');
                    break;
                case 'maintenance':
                    this.renderTrendChart('maintenanceTrendChart', this.summary.charts.maintenance_trend, '维保费用 (元)', 'rgba(153, 102, 255, 0.6)');
                    break;
            }
        },
        
        // (重构) 将部门车辆分布图的渲染逻辑独立出来
        renderVehiclesPerDeptChart() {
            const chartData = this.summary.charts.vehicles_per_department;
            if (!chartData) return;
            this.renderChart('vehiclesPerDeptChart', 'bar', chartData, { label: '车辆数量' });
        },
        
        // (新增) 创建一个通用的趋势图渲染方法，减少重复代码
        renderTrendChart(canvasId, chartData, label, color) {
            if (!chartData) return;
            this.renderChart(canvasId, 'line', chartData, { label, backgroundColor: color, borderColor: color.replace('0.6', '1') });
        },

        // (新增) 创建一个最核心的、通用的图表渲染引擎
        renderChart(canvasId, type, chartData, datasetOptions) {
            const ctx = document.getElementById(canvasId);
            if (!ctx) return; // 如果canvas不存在则退出

            const chartInstance = this.charts[canvasId];
            if (chartInstance) {
                chartInstance.destroy();
            }

            this.charts[canvasId] = new Chart(ctx.getContext('2d'), {
                type: type,
                data: {
                    labels: chartData.labels,
                    datasets: [{
                        ...datasetOptions,
                        data: chartData.data,
                        borderWidth: 2, // 线条稍粗一些
                        pointRadius: 4, // 数据点更明显
                        pointHoverRadius: 6, // 悬浮时数据点更大
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    scales: { 
                        y: { 
                            beginAtZero: true,
                            ticks: { // 格式化Y轴标签，例如加上单位
                                callback: function(value, index, values) {
                                    if (datasetOptions.unit) {
                                        return `${value} ${datasetOptions.unit}`;
                                    }
                                    return value;
                                }
                            }
                        } 
                    },
                    // (新增) 交互和动画配置
                    interaction: {
                        intersect: false,
                        mode: 'index',
                    },
                    plugins: {
                        tooltip: {
                            callbacks: {
                                label: function(context) {
                                    let label = context.dataset.label || '';
                                    if (label) {
                                        label += ': ';
                                    }
                                    if (context.parsed.y !== null) {
                                        // 在提示中也加上单位
                                        label += `${context.parsed.y}${datasetOptions.unit || ''}`;
                                    }
                                    return label;
                                }
                            }
                        }
                    },
                    // (新增) 加载动画配置
                    animation: {
                        duration: 1000, // 动画持续1秒
                        easing: 'easeInOutQuad' // 缓动效果
                    }
                }
            });
        }
    }
}).mount('#app'); // 将这个 Vue 应用挂载到 DOM 中 id 为 "app" 的 HTML 元素上
                   // 这句话告诉 Vue：“请接管那个 id='app' 的 div，并在其中渲染我们的应用”
