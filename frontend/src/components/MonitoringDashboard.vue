<template>
  <div class="dashboard-container">
    <div v-if="!hasAccess">
      <h1>Доступ запрещен</h1>
      <p>У вас нет прав для просмотра этой страницы. Только администраторы могут просматривать мониторинг системы.</p>
    </div>
    <div v-else>
      <h1>Мониторинг системы</h1>
      
      <!-- System Metrics Cards -->
      <div class="metrics-grid">
        <div class="metric-card">
          <h3>CPU</h3>
          <div class="metric-value">{{ systemMetrics.cpu?.percent }}%</div>
          <div class="metric-chart">
            <canvas ref="cpuChart"></canvas>
          </div>
        </div>
        
        <div class="metric-card">
          <h3>Память</h3>
          <div class="metric-value">{{ systemMetrics.memory?.percent }}%</div>
          <div class="metric-chart">
            <canvas ref="memoryChart"></canvas>
          </div>
        </div>
        
        <div class="metric-card">
          <h3>Диск</h3>
          <div class="metric-value">{{ systemMetrics.disk?.percent }}%</div>
          <div class="metric-chart">
            <canvas ref="diskChart"></canvas>
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
import { ref, onMounted, onUnmounted, nextTick, computed } from 'vue';
import { useUserStore } from '@/stores/UserStore';

export default {
  name: 'MonitoringDashboard',
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
    const hasAccess = ref(false);
    
    // Check if user is staff
    const checkAccess = () => {
      hasAccess.value = userStore.currentUser && userStore.currentUser.role === 'admin';
    };
    
    // Get auth headers
    const getAuthHeaders = () => {
      const token = userStore.currentUser?.accessToken;
      return token ? { Authorization: `Bearer ${token}` } : {};
    };
    
    // Chart references
    const cpuChart = ref(null);
    const memoryChart = ref(null);
    const diskChart = ref(null);
    
    // Fetch system metrics
    const fetchSystemMetrics = async () => {
      try {
        const headers = getAuthHeaders();
        const response = await axios.get('/api/monitoring/system/', { headers });
        systemMetrics.value = response.data;
      } catch (error) {
        console.error('Error fetching system metrics:', error);
        if (error.response && (error.response.status === 403 || error.response.status === 401)) {
          hasAccess.value = false;
        }
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
        if (error.response && (error.response.status === 403 || error.response.status === 401)) {
          hasAccess.value = false;
        }
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
        if (error.response && (error.response.status === 403 || error.response.status === 401)) {
          hasAccess.value = false;
        }
      }
    };
    
    // Initialize data
    const initializeData = async () => {
      checkAccess();
      
      if (!hasAccess.value) {
        return;
      }
      
      await Promise.all([
        fetchSystemMetrics(),
        fetchTaskStats(),
        fetchHistoricalStats()
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
        }
      }, 30000);
      
      // Clean up interval on component unmount
      onUnmounted(() => {
        clearInterval(refreshInterval);
      });
    });
    
    return {
      systemMetrics,
      taskStats,
      historicalStats,
      activeTab,
      hasAccess,
      cpuChart,
      memoryChart,
      diskChart
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
  height: 100px;
  display: flex;
  align-items: center;
  justify-content: center;
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