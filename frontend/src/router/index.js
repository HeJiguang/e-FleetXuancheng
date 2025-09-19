import { createRouter, createWebHashHistory } from 'vue-router'
import OverallOverview from '../views/OverallOverview.vue'
import DepartmentOverview from '../views/DepartmentOverview.vue';
import VehicleOverview from '../views/VehicleOverview.vue';

const router = createRouter({
  history: createWebHashHistory(import.meta.env.BASE_URL), // (修正) 添加 history base
  routes: [
    {
      path: '/',
      name: 'overview',
      component: OverallOverview
    },
    {
      path: '/departments',
      name: 'departments',
      component: DepartmentOverview
    },
    {
      path: '/vehicles',
      name: 'vehicles',
      component: VehicleOverview
    },
    {
      path: '/data-management',
      name: 'data-management',
      component: () => import('../views/DataManagement.vue') // (新增)
    },
    {
      path: '/vehicle/:plate_number',
      name: 'VehicleDetail',
      component: () => import('../views/VehicleDetail.vue'),
      props: true
    },
    {
      path: '/department/:id',
      name: 'DepartmentDetail',
      component: () => import('../views/DepartmentDetail.vue'),
      props: true
    }
  ]
})

export default router
