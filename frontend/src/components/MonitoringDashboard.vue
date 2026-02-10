<template>
  <div>
    <UiHeader />
    <div class="dashboard-container">
      <h1>Мониторинг системы</h1>
      
      <!-- System Metrics Cards -->
      <div class="metrics-grid">
        <div class="metric-card">
          <h3>CPU</h3>
          <div class="metric-value">{{ Math.round(systemMetrics.cpu?.percent) }}%</div>
          <div class="metric-chart">
            <Line
              :data="cpuChartData"
              :options="chartOptions"
              class="chart-canvas"
            />
          </div>
        </div>

        <div class="metric-card">
          <h3>Память</h3>
          <div class="metric-value">{{ Math.round(systemMetrics.memory?.percent) }}%</div>
          <div class="metric-chart">
            <Line
              :data="memoryChartData"
              :options="chartOptions"
              class="chart-canvas"
            />
          </div>
        </div>

        <div class="metric-card">
          <h3>Диск</h3>
          <div class="metric-value">{{ Math.round(systemMetrics.disk?.percent) }}%</div>
          <div class="metric-chart">
            <Line
              :data="diskChartData"
              :options="chartOptions"
              class="chart-canvas"
            />
          </div>
        </div>

      </div>
      
      <!-- Task Statistics -->
      <div class="task-stats-container">
        <h2>Статистика задач</h2>
        <div class="stats-grid">
          <div class="stat-card">
            <h3>Всего задач</h3>
            <div class="stat-value">{{ taskStats.total }}</div>
          </div>
          <div class="stat-card pending">
            <h3>В очереди</h3>
            <div class="stat-value">{{ taskStats.pending }}</div>
          </div>
          <div class="stat-card running">
            <h3>Выполняется</h3>
            <div class="stat-value">{{ taskStats.running }}</div>
          </div>
          <div class="stat-card accepted">
            <h3>Завершено</h3>
            <div class="stat-value">{{ taskStats.accepted }}</div>
          </div>
          <div class="stat-card failed">
            <h3>Ошибки</h3>
            <div class="stat-value">{{ taskStats.failed }}</div>
          </div>
        </div>
      </div>
      
      <!-- Historical Data -->
      <div class="historical-data-container">
        <h2>Исторические данные</h2>
        <div class="history-tabs">
          <button 
            :class="{ active: activeTab === 'daily' }" 
            @click="activeTab = 'daily'"
          >
            За день
          </button>
          <button 
            :class="{ active: activeTab === 'weekly' }" 
            @click="activeTab = 'weekly'"
          >
            За неделю
          </button>
          <button 
            :class="{ active: activeTab === 'monthly' }" 
            @click="activeTab = 'monthly'"
          >
            За месяц
          </button>
        </div>
        
        <div class="history-content">
          <div v-if="activeTab === 'daily'" class="history-stats">
            <div class="stat-card">
              <h3>Всего задач</h3>
              <div class="stat-value">{{ historicalStats.daily?.total }}</div>
            </div>
            <div class="stat-card pending">
              <h3>В очереди</h3>
              <div class="stat-value">{{ historicalStats.daily?.pending }}</div>
            </div>
            <div class="stat-card running">
              <h3>Выполняется</h3>
              <div class="stat-value">{{ historicalStats.daily?.running }}</div>
            </div>
            <div class="stat-card accepted">
              <h3>Завершено</h3>
              <div class="stat-value">{{ historicalStats.daily?.accepted }}</div>
            </div>
            <div class="stat-card failed">
              <h3>Ошибки</h3>
              <div class="stat-value">{{ historicalStats.daily?.failed }}</div>
            </div>
          </div>
          
          <div v-if="activeTab === 'weekly'" class="history-stats">
            <div class="stat-card">
              <h3>Всего задач</h3>
              <div class="stat-value">{{ historicalStats.weekly?.total }}</div>
            </div>
            <div class="stat-card pending">
              <h3>В очереди</h3>
              <div class="stat-value">{{ historicalStats.weekly?.pending }}</div>
            </div>
            <div class="stat-card running">
              <h3>Выполняется</h3>
              <div class="stat-value">{{ historicalStats.weekly?.running }}</div>
            </div>
            <div class="stat-card accepted">
              <h3>Завершено</h3>
              <div class="stat-value">{{ historicalStats.weekly?.accepted }}</div>
            </div>
            <div class="stat-card failed">
              <h3>Ошибки</h3>
              <div class="stat-value">{{ historicalStats.weekly?.failed }}</div>
            </div>
          </div>
          
          <div v-if="activeTab === 'monthly'" class="history-stats">
            <div class="stat-card">
              <h3>Всего задач</h3>
              <div class="stat-value">{{ historicalStats.monthly?.total }}</div>
            </div>
            <div class="stat-card pending">
              <h3>В очереди</h3>
              <div class="stat-value">{{ historicalStats.monthly?.pending }}</div>
            </div>
            <div class="stat-card running">
              <h3>Выполняется</h3>
              <div class="stat-value">{{ historicalStats.monthly?.running }}</div>
            </div>
            <div class="stat-card accepted">
              <h3>Завершено</h3>
              <div class="stat-value">{{ historicalStats.monthly?.accepted }}</div>
            </div>
            <div class="stat-card failed">
              <h3>Ошибки</h3>
              <div class="stat-value">{{ historicalStats.monthly?.failed }}</div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import axios from 'axios';
import { ref, onMounted, onUnmounted, nextTick } from 'vue';
import { useUserStore } from '@/stores/UserStore';
import UiHeader from '@/components/ui/UiHeader.vue';
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Title,
  Tooltip,
  Legend,
  Filler
} from 'chart.js';
import { Line } from 'vue-chartjs';

// Регистрация компонентов Chart.js
ChartJS.register(
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Title,
  Tooltip,
  Legend,
  Filler
);

export default {
  name: 'MonitoringDashboard',
  components: {
    UiHeader,
    Line
  },
  setup() {
    const userStore = useUserStore();
    const systemMetrics = ref({});
    const taskStats = ref({});
    const historicalStats = ref({
      daily: {},
      weekly: {},
      monthly: {}
    });
    const activeTab = ref('daily');
    const hasAccess = ref(true); // Всегда true, так как теперь доступ разрешен всем авторизованным пользователям
    
    // Get auth headers
    const getAuthHeaders = () => {
      const token = userStore.currentUser?.accessToken;
      return token ? { Authorization: `Bearer ${token}` } : {};
    };
    
    
    // Fetch system metrics
    const fetchSystemMetrics = async () => {
      try {
        const headers = getAuthHeaders();
        const response = await axios.get('/api/monitoring/system/', { headers });
        systemMetrics.value = response.data;
      } catch (error) {
        console.error('Error fetching system metrics:', error);
        // Не изменяем hasAccess, так как доступ теперь разрешен всем авторизованным пользователям
      }
    };

    // Fetch task statistics
    const fetchTaskStats = async () => {
      try {
        const headers = getAuthHeaders();
        const response = await axios.get('/api/monitoring/tasks/', { headers });
        taskStats.value = response.data;
      } catch (error) {
        console.error('Error fetching task statistics:', error);
        // Не изменяем hasAccess, так как доступ теперь разрешен всем авторизованным пользователям
      }
    };

    // Fetch historical statistics
    const fetchHistoricalStats = async () => {
      try {
        const headers = getAuthHeaders();
        const response = await axios.get('/api/monitoring/historical/', { headers });
        historicalStats.value = response.data;
      } catch (error) {
        console.error('Error fetching historical statistics:', error);
        // Не изменяем hasAccess, так как доступ теперь разрешен всем авторизованным пользователям
      }
    };
    
    // Fetch historical metrics for charts
    const fetchHistoricalMetrics = async () => {
      try {
        const headers = getAuthHeaders();
        const response = await axios.get('/api/monitoring/historical-metrics/', { headers });
        
        
        // Обновляем данные для графиков, создавая новые объекты для реактивности
        // Проверяем, что количество меток и данных совпадает
        const timestamps = response.data.timestamps || [];
        const cpuHistory = response.data.cpu_history || [];
        const memoryHistory = response.data.memory_history || [];
        const diskHistory = response.data.disk_history || [];
        
        // Убедимся, что длина массивов совпадает
        const minLength = Math.min(timestamps.length, cpuHistory.length, memoryHistory.length, diskHistory.length);
        
        const newCpuData = {
          labels: timestamps.slice(0, minLength),
          datasets: [
            {
              label: 'Загрузка CPU (%)',
              data: cpuHistory.slice(0, minLength),
              borderColor: '#36A2EB',
              backgroundColor: 'rgba(54, 162, 235, 0.1)',
              tension: 0.4,
              fill: true
            }
          ]
        };
        
        const newMemoryData = {
          labels: timestamps.slice(0, minLength),
          datasets: [
            {
              label: 'Использование памяти (%)',
              data: memoryHistory.slice(0, minLength),
              borderColor: '#FF6384',
              backgroundColor: 'rgba(255, 99, 132, 0.1)',
              tension: 0.4,
              fill: true
            }
          ]
        };
        
        const newDiskData = {
          labels: timestamps.slice(0, minLength),
          datasets: [
            {
              label: 'Использование диска (%)',
              data: diskHistory.slice(0, minLength),
              borderColor: '#FFCE56',
              backgroundColor: 'rgba(255, 206, 86, 0.1)',
              tension: 0.4,
              fill: true
            }
          ]
        };
        
        // Присваиваем новые объекты для обеспечения реактивности
        cpuChartData.value = newCpuData;
        memoryChartData.value = newMemoryData;
        diskChartData.value = newDiskData;
      } catch (error) {
        console.error('Error fetching historical metrics:', error);
        
        // Устанавливаем минимальные данные для отображения пустого графика
        const defaultLabels = ['1 мин', '5 мин', '10 мин', '15 мин', '20 мин', '25 мин', '30 мин'];
        cpuChartData.value = {
          labels: defaultLabels,
          datasets: [
            {
              label: 'Загрузка CPU (%)',
              data: [],
              borderColor: '#36A2EB',
              backgroundColor: 'rgba(54, 162, 235, 0.1)',
              tension: 0.4,
              fill: true
            }
          ]
        };
        
        memoryChartData.value = {
          labels: defaultLabels,
          datasets: [
            {
              label: 'Использование памяти (%)',
              data: [],
              borderColor: '#FF6384',
              backgroundColor: 'rgba(255, 99, 132, 0.1)',
              tension: 0.4,
              fill: true
            }
          ]
        };
        
        diskChartData.value = {
          labels: defaultLabels,
          datasets: [
            {
              label: 'Использование диска (%)',
              data: [],
              borderColor: '#FFCE56',
              backgroundColor: 'rgba(255, 206, 86, 0.1)',
              tension: 0.4,
              fill: true
            }
          ]
        };
      }
    };

    // Initialize data
    const initializeData = async () => {
      // Убираем проверку доступа, так как теперь она разрешена для всех авторизованных пользователей
      await Promise.all([
        fetchSystemMetrics(),
        fetchTaskStats(),
        fetchHistoricalStats(),
        fetchHistoricalMetrics()
      ]);

      // Update charts after data is loaded
      await nextTick();
      // Note: Chart initialization would happen here if we had chart libraries
    };
    
    onMounted(() => {
      initializeData();
      
      // Refresh data every 30 seconds if user has access
      const refreshInterval = setInterval(() => {
        if (hasAccess.value) {
          fetchSystemMetrics();
          fetchTaskStats();
          fetchHistoricalStats();
          fetchHistoricalMetrics();
        }
      }, 30000);
      
      // Clean up interval on component unmount
      onUnmounted(() => {
        clearInterval(refreshInterval);
      });
    });
    

    // Данные для графиков
    const cpuChartData = ref({
      labels: [],
      datasets: [
        {
          label: 'Загрузка CPU (%)',
          data: [],
          borderColor: '#36A2EB',
          backgroundColor: 'rgba(54, 162, 235, 0.1)',
          tension: 0.4,
          fill: true
        }
      ]
    });

    const memoryChartData = ref({
      labels: [],
      datasets: [
        {
          label: 'Использование памяти (%)',
          data: [],
          borderColor: '#FF6384',
          backgroundColor: 'rgba(255, 99, 132, 0.1)',
          tension: 0.4,
          fill: true
        }
      ]
    });

    const diskChartData = ref({
      labels: [],
      datasets: [
        {
          label: 'Использование диска (%)',
          data: [],
          borderColor: '#FFCE56',
          backgroundColor: 'rgba(255, 206, 86, 0.1)',
          tension: 0.4,
          fill: true
        }
      ]
    });

    // Опции для графиков
    const chartOptions = ref({
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: {
          position: 'top',
        },
        title: {
          display: false,
        }
      },
      scales: {
        y: {
          beginAtZero: true,
          max: 100,
          ticks: {
            callback: function(value) {
              return value + '%';
            }
          }
        }
      }
    });

    return {
      systemMetrics,
      taskStats,
      historicalStats,
      activeTab,
      hasAccess,
      cpuChartData,
      memoryChartData,
      diskChartData,
      chartOptions
    };
  }
};
</script>

<style scoped>
.dashboard-container {
  padding: 20px;
  max-width: 1200px;
  margin: 0 auto;
}

.metrics-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
  gap: 20px;
  margin-bottom: 30px;
}

.metric-card {
  background: white;
  border-radius: 8px;
  padding: 20px;
  box-shadow: 0 2px 10px rgba(0,0,0,0.1);
  text-align: center;
}

.metric-card h3 {
  margin-top: 0;
  color: #333;
}

.metric-value {
  font-size: 2em;
  font-weight: bold;
  margin: 10px 0;
}

.metric-chart {
  height: 150px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.chart-canvas {
  width: 100%;
  height: 100%;
}

.metric-details {
  margin-top: 10px;
  text-align: left;
  font-size: 0.9em;
  color: #666;
}

.task-stats-container, .historical-data-container {
  background: white;
  border-radius: 8px;
  padding: 20px;
  box-shadow: 0 2px 10px rgba(0,0,0,0.1);
  margin-bottom: 30px;
}

.stats-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
  gap: 15px;
  margin-top: 20px;
}

.history-tabs {
  display: flex;
  margin-bottom: 20px;
  border-bottom: 1px solid #ddd;
}

.history-tabs button {
  padding: 10px 20px;
  border: none;
  background: transparent;
  cursor: pointer;
  border-bottom: 3px solid transparent;
}

.history-tabs button.active {
  border-bottom-color: #007bff;
  color: #007bff;
}

.history-content {
  padding-top: 15px;
}

.history-stats {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
  gap: 15px;
}

.stat-card {
  background: #f8f9fa;
  border-radius: 6px;
  padding: 15px;
  text-align: center;
  border-left: 4px solid #007bff;
}

.stat-card.pending {
  border-left-color: #ffc107;
}

.stat-card.running {
  border-left-color: #17a2b8;
}

.stat-card.accepted {
  border-left-color: #28a745;
}

.stat-card.failed {
  border-left-color: #dc3545;
}

.stat-card h3 {
  margin: 0 0 10px 0;
  font-size: 0.9em;
  color: #666;
}

.stat-value {
  font-size: 1.5em;
  font-weight: bold;
  color: #333;
}
</style>