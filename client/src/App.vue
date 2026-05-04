<template>
  <div class="app" :class="{ 'sidebar-collapsed': sidebarCollapsed }">
    <Sidebar
      @show-profile-details="showProfileDetails = true"
      @show-tasks="showTasks = true"
      @collapse-change="sidebarCollapsed = $event"
    />
    <div class="content-area">
      <FilterBar />
      <main class="main-content">
      <router-view v-slot="{ Component }">
        <transition name="page" mode="out-in">
          <component :is="Component" />
        </transition>
      </router-view>
    </main>
    </div>

    <ProfileDetailsModal
      :is-open="showProfileDetails"
      @close="showProfileDetails = false"
    />

    <TasksModal
      :is-open="showTasks"
      :tasks="tasks"
      @close="showTasks = false"
      @add-task="addTask"
      @delete-task="deleteTask"
      @toggle-task="toggleTask"
    />
  </div>
</template>

<script>
import { ref, onMounted, computed } from 'vue'
import { api } from './api'
import { useAuth } from './composables/useAuth'
import { useI18n } from './composables/useI18n'
import Sidebar from './components/Sidebar.vue'
import FilterBar from './components/FilterBar.vue'
import ProfileDetailsModal from './components/ProfileDetailsModal.vue'
import TasksModal from './components/TasksModal.vue'

export default {
  name: 'App',
  components: {
    Sidebar,
    FilterBar,
    ProfileDetailsModal,
    TasksModal
  },
  setup() {
    const { currentUser } = useAuth()
    const { t } = useI18n()
    const showProfileDetails = ref(false)
    const showTasks = ref(false)
    const sidebarCollapsed = ref(false)
    const apiTasks = ref([])

    // Merge mock tasks from currentUser with API tasks
    const tasks = computed(() => {
      return [...currentUser.value.tasks, ...apiTasks.value]
    })

    const loadTasks = async () => {
      try {
        apiTasks.value = await api.getTasks()
      } catch (err) {
        console.error('Failed to load tasks:', err)
      }
    }

    const addTask = async (taskData) => {
      try {
        const newTask = await api.createTask(taskData)
        // Add new task to the beginning of the array
        apiTasks.value.unshift(newTask)
      } catch (err) {
        console.error('Failed to add task:', err)
      }
    }

    const deleteTask = async (taskId) => {
      try {
        // Check if it's a mock task (from currentUser)
        const isMockTask = currentUser.value.tasks.some(t => t.id === taskId)

        if (isMockTask) {
          // Remove from mock tasks
          const index = currentUser.value.tasks.findIndex(t => t.id === taskId)
          if (index !== -1) {
            currentUser.value.tasks.splice(index, 1)
          }
        } else {
          // Remove from API tasks
          await api.deleteTask(taskId)
          apiTasks.value = apiTasks.value.filter(t => t.id !== taskId)
        }
      } catch (err) {
        console.error('Failed to delete task:', err)
      }
    }

    const toggleTask = async (taskId) => {
      try {
        // Check if it's a mock task (from currentUser)
        const mockTask = currentUser.value.tasks.find(t => t.id === taskId)

        if (mockTask) {
          // Toggle mock task status
          mockTask.status = mockTask.status === 'pending' ? 'completed' : 'pending'
        } else {
          // Toggle API task
          const updatedTask = await api.toggleTask(taskId)
          const index = apiTasks.value.findIndex(t => t.id === taskId)
          if (index !== -1) {
            apiTasks.value[index] = updatedTask
          }
        }
      } catch (err) {
        console.error('Failed to toggle task:', err)
      }
    }

    onMounted(loadTasks)

    return {
      t,
      showProfileDetails,
      showTasks,
      sidebarCollapsed,
      tasks,
      addTask,
      deleteTask,
      toggleTask
    }
  }
}
</script>

<style>
:root {
  /* Background */
  --bg-page:         #f1f5f9;
  --bg-surface:      #ffffff;
  --bg-subtle:       #f8fafc;

  /* Borders */
  --border:          #e2e8f0;
  --border-light:    #f1f5f9;

  /* Text */
  --text-primary:    #0f172a;
  --text-secondary:  #475569;
  --text-muted:      #94a3b8;
  --text-body:       #334155;

  /* Accent (blue) */
  --accent:          #2563eb;
  --accent-hover:    #1d4ed8;
  --accent-light:    #eff6ff;
  --accent-fg:       #60a5fa;

  /* Status */
  --success:         #059669;
  --success-bg:      #d1fae5;
  --success-text:    #065f46;
  --warning:         #d97706;
  --warning-bg:      #fef3c7;
  --warning-text:    #92400e;
  --danger:          #dc2626;
  --danger-bg:       #fee2e2;
  --danger-text:     #991b1b;
  --info:            #2563eb;
  --info-bg:         #dbeafe;
  --info-text:       #1e40af;

  /* Radius */
  --radius-sm:  6px;
  --radius-md:  8px;
  --radius-lg:  12px;

  /* Shadows */
  --shadow-sm:  0 1px 3px rgba(0,0,0,0.04), 0 1px 2px -1px rgba(0,0,0,0.04);
  --shadow-md:  0 4px 8px -2px rgba(0,0,0,0.08), 0 2px 4px -2px rgba(0,0,0,0.04);
  --shadow-lg:  0 12px 24px -4px rgba(0,0,0,0.10), 0 4px 8px -4px rgba(0,0,0,0.05);

  /* Transitions */
  --t-fast: all 0.15s ease;
  --t-base: all 0.2s ease;
  --t-slow: all 0.3s ease;
}

* {
  margin: 0;
  padding: 0;
  box-sizing: border-box;
}

body {
  font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
  background: var(--bg-page);
  color: #1e293b;
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
}

.app {
  display: flex;
  flex-direction: row;
  min-height: 100vh;
}

.content-area {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  min-width: 0;
  /* Mirror the sidebar's width transition so the content area expands
     at the same speed as the sidebar collapses. */
  transition: margin-left 0.25s ease;
}


.main-content {
  flex: 1;
  padding: 1.5rem 2rem;
  overflow-y: auto;
}

.page-header {
  margin-bottom: 2rem;
}

.page-header h2 {
  font-size: 1.75rem;
  font-weight: 700;
  color: var(--text-primary);
  margin-bottom: 0.375rem;
  letter-spacing: -0.03em;
  line-height: 1.2;
}

.page-header p {
  color: var(--text-muted);
  font-size: 0.875rem;
  line-height: 1.5;
}

.stats-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
  gap: 1.25rem;
  margin-bottom: 1.5rem;
}

.stat-card {
  background: var(--bg-surface);
  padding: 1.5rem;
  border-radius: var(--radius-lg);
  border: 1px solid var(--border);
  box-shadow: var(--shadow-sm);
  transition: var(--t-base);
  position: relative;
  overflow: hidden;
}

.stat-card:hover {
  box-shadow: var(--shadow-md);
  transform: translateY(-1px);
}

.stat-card::before {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  height: 3px;
  background: var(--border);
  border-radius: var(--radius-lg) var(--radius-lg) 0 0;
}

.stat-card.success::before {
  background: var(--success);
}

.stat-card.warning::before {
  background: var(--warning);
}

.stat-card.danger::before {
  background: var(--danger);
}

.stat-card.info::before {
  background: var(--info);
}

.stat-label {
  color: var(--text-muted);
  font-size: 0.75rem;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.06em;
  margin-bottom: 0.75rem;
}

.stat-value {
  font-size: 2.25rem;
  font-weight: 700;
  color: var(--text-primary);
  letter-spacing: -0.03em;
  line-height: 1;
}

.card {
  background: var(--bg-surface);
  border-radius: var(--radius-lg);
  padding: 1.5rem;
  border: 1px solid var(--border);
  margin-bottom: 1.5rem;
  box-shadow: var(--shadow-sm);
  transition: var(--t-base);
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 1.25rem;
  padding-bottom: 1rem;
  border-bottom: 1px solid var(--border-light);
}

.card-title {
  font-size: 1rem;
  font-weight: 600;
  color: var(--text-primary);
  letter-spacing: -0.01em;
}

.table-container {
  overflow-x: auto;
}

table {
  width: 100%;
  border-collapse: collapse;
}

thead {
  background: var(--bg-subtle);
  border-top: 1px solid var(--border);
  border-bottom: 1px solid var(--border);
}

th {
  text-align: left;
  padding: 0.625rem 1rem;
  font-weight: 700;
  color: var(--text-secondary);
  font-size: 0.688rem;
  text-transform: uppercase;
  letter-spacing: 0.07em;
}

td {
  padding: 0.875rem 1rem;
  border-top: 1px solid var(--border-light);
  color: var(--text-body);
  font-size: 0.875rem;
  line-height: 1.4;
}

tbody tr {
  transition: background-color 0.15s ease;
}

tbody tr:hover {
  background: var(--bg-subtle);
}

.badge {
  display: inline-flex;
  align-items: center;
  padding: 0.25rem 0.625rem;
  border-radius: var(--radius-sm);
  font-size: 0.688rem;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.04em;
  line-height: 1;
}

.badge.success {
  background: var(--success-bg);
  color: var(--success-text);
}

.badge.warning {
  background: var(--warning-bg);
  color: var(--warning-text);
}

.badge.danger {
  background: var(--danger-bg);
  color: var(--danger-text);
}

.badge.info {
  background: var(--info-bg);
  color: var(--info-text);
}

.badge.increasing {
  background: #d1fae5;
  color: #065f46;
}

.badge.decreasing {
  background: #fecaca;
  color: #991b1b;
}

.badge.stable {
  background: #e0e7ff;
  color: #3730a3;
}

.badge.high {
  background: #fecaca;
  color: #991b1b;
}

.badge.medium {
  background: #fed7aa;
  color: #92400e;
}

.badge.low {
  background: #dbeafe;
  color: #1e40af;
}

.page-enter-active,
.page-leave-active {
  transition: opacity 0.18s ease, transform 0.18s ease;
}

.page-enter-from {
  opacity: 0;
  transform: translateY(6px);
}

.page-leave-to {
  opacity: 0;
  transform: translateY(-4px);
}

.loading {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 4rem;
  color: var(--text-muted);
  font-size: 0.875rem;
  gap: 0.75rem;
}

.loading::before {
  content: '';
  width: 28px;
  height: 28px;
  border: 2px solid var(--border);
  border-top-color: var(--accent);
  border-radius: 50%;
  animation: spin 0.7s linear infinite;
}

@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}

.error {
  background: var(--danger-bg);
  border: 1px solid #fca5a5;
  color: var(--danger-text);
  padding: 1rem 1.25rem;
  border-radius: var(--radius-md);
  font-size: 0.875rem;
  margin: 1rem 0;
}
</style>
