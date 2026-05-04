<template>
  <nav class="sidebar" :class="{ collapsed: isCollapsed }">
    <!-- Brand Section -->
    <div class="sidebar-brand">
      <div class="brand-logo">
        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg" aria-hidden="true" class="brand-icon">
          <path
            d="M12 2a1 1 0 0 1 .894.553l1.618 3.235 3.573.52a1 1 0 0 1 .555 1.705l-2.587 2.52.611 3.558a1 1 0 0 1-1.451 1.054L12 13.347l-3.213 1.698a1 1 0 0 1-1.451-1.054l.611-3.558-2.587-2.52a1 1 0 0 1 .555-1.706l3.573-.519 1.618-3.235A1 1 0 0 1 12 2z"
            fill="none"
          />
          <path
            d="M12 15.5a3.5 3.5 0 1 0 0 7 3.5 3.5 0 0 0 0-7zM9.5 19a2.5 2.5 0 1 1 5 0 2.5 2.5 0 0 1-5 0z"
            fill="#2563eb"
          />
          <path
            d="M12 1c.55 0 1.05.3 1.3.79l1.42 2.84 3.13.45c.54.08.98.46 1.14.98.16.52.02 1.08-.37 1.46L16.18 9.6l.54 3.12c.09.54-.13 1.08-.57 1.4-.44.32-1.02.36-1.5.1L12 12.56l-2.65 1.4c-.07.03-.13.06-.2.08v3.46a1 1 0 0 1-2 0v-3.9c-.18-.13-.33-.29-.44-.48-.44-.32-.66-.86-.57-1.4l.54-3.12-2.44-2.08c-.39-.38-.53-.94-.37-1.46.16-.52.6-.9 1.14-.98l3.13-.45L10.7 1.79C10.95 1.3 11.45 1 12 1z"
            fill="#2563eb"
            opacity="0.3"
          />
          <circle cx="12" cy="12" r="3" fill="#2563eb" />
          <path
            d="M12 6a1 1 0 0 1 .894.553l.92 1.838 2.027.295a1 1 0 0 1 .555 1.705l-1.467 1.43.347 2.018a1 1 0 0 1-1.451 1.054L12 13.944l-1.825.965a1 1 0 0 1-1.451-1.054l.347-2.018-1.467-1.43a1 1 0 0 1 .555-1.705l2.027-.295L11.106 6.553A1 1 0 0 1 12 6z"
            fill="#2563eb"
          />
        </svg>
        <span class="brand-name">{{ t('nav.companyName') }}</span>
      </div>
      <div class="brand-subtitle">{{ t('nav.subtitle') }}</div>

      <!-- Toggle button sits in the brand area -->
      <button
        class="toggle-btn"
        @click="toggleSidebar"
        :aria-label="isCollapsed ? 'Expand sidebar' : 'Collapse sidebar'"
        :title="isCollapsed ? 'Expand sidebar' : 'Collapse sidebar'"
      >
        <!-- Chevron left when expanded, chevron right when collapsed -->
        <svg viewBox="0 0 18 18" fill="none" xmlns="http://www.w3.org/2000/svg" aria-hidden="true">
          <path
            v-if="!isCollapsed"
            d="M11 14L6 9l5-5"
            stroke="currentColor"
            stroke-width="1.75"
            stroke-linecap="round"
            stroke-linejoin="round"
          />
          <path
            v-else
            d="M7 4l5 5-5 5"
            stroke="currentColor"
            stroke-width="1.75"
            stroke-linecap="round"
            stroke-linejoin="round"
          />
        </svg>
      </button>
    </div>

    <!-- Navigation Section -->
    <div class="sidebar-nav">
      <router-link
        v-for="item in navItems"
        :key="item.path"
        :to="item.path"
        class="nav-item"
        :class="{ active: isActive(item.path) }"
        :title="isCollapsed ? item.label : ''"
      >
        <!-- Home icon -->
        <svg v-if="item.icon === 'home'" class="nav-icon" viewBox="0 0 18 18" fill="none" xmlns="http://www.w3.org/2000/svg" aria-hidden="true">
          <path d="M1 8L9 1l8 7v8a1 1 0 0 1-1 1h-4v-4H6v4H2a1 1 0 0 1-1-1V8z" stroke="currentColor" stroke-width="1.5" stroke-linejoin="round" fill="none"/>
        </svg>

        <!-- Box/Cube icon -->
        <svg v-else-if="item.icon === 'box'" class="nav-icon" viewBox="0 0 18 18" fill="none" xmlns="http://www.w3.org/2000/svg" aria-hidden="true">
          <path d="M9 1L16 5v8L9 17 2 13V5L9 1z" stroke="currentColor" stroke-width="1.5" stroke-linejoin="round" fill="none"/>
          <path d="M9 1v16M2 5l7 4 7-4" stroke="currentColor" stroke-width="1.5" stroke-linejoin="round"/>
        </svg>

        <!-- Clipboard icon -->
        <svg v-else-if="item.icon === 'clipboard'" class="nav-icon" viewBox="0 0 18 18" fill="none" xmlns="http://www.w3.org/2000/svg" aria-hidden="true">
          <rect x="3" y="3" width="12" height="14" rx="1.5" stroke="currentColor" stroke-width="1.5" fill="none"/>
          <path d="M6 1h6a1 1 0 0 1 1 1v2H5V2a1 1 0 0 1 1-1z" stroke="currentColor" stroke-width="1.5" fill="none"/>
          <path d="M6 8h6M6 11h4" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/>
        </svg>

        <!-- Dollar sign icon -->
        <svg v-else-if="item.icon === 'dollar'" class="nav-icon" viewBox="0 0 18 18" fill="none" xmlns="http://www.w3.org/2000/svg" aria-hidden="true">
          <circle cx="9" cy="9" r="7.5" stroke="currentColor" stroke-width="1.5" fill="none"/>
          <path d="M9 4v10M6.5 6.5a2.5 2.5 0 0 1 5 0c0 1.38-1.12 2.5-2.5 2.5a2.5 2.5 0 0 1 0 5" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/>
        </svg>

        <!-- Bar chart icon -->
        <svg v-else-if="item.icon === 'chart'" class="nav-icon" viewBox="0 0 18 18" fill="none" xmlns="http://www.w3.org/2000/svg" aria-hidden="true">
          <rect x="2" y="10" width="3" height="6" rx="0.5" stroke="currentColor" stroke-width="1.5" fill="none"/>
          <rect x="7.5" y="6" width="3" height="10" rx="0.5" stroke="currentColor" stroke-width="1.5" fill="none"/>
          <rect x="13" y="2" width="3" height="14" rx="0.5" stroke="currentColor" stroke-width="1.5" fill="none"/>
          <path d="M1 17h16" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/>
        </svg>

        <!-- Document icon -->
        <svg v-else-if="item.icon === 'document'" class="nav-icon" viewBox="0 0 18 18" fill="none" xmlns="http://www.w3.org/2000/svg" aria-hidden="true">
          <path d="M10 1H4a1 1 0 0 0-1 1v14a1 1 0 0 0 1 1h10a1 1 0 0 0 1-1V6l-5-5z" stroke="currentColor" stroke-width="1.5" stroke-linejoin="round" fill="none"/>
          <path d="M10 1v5h5" stroke="currentColor" stroke-width="1.5" stroke-linejoin="round"/>
          <path d="M5 10h8M5 13h5" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/>
        </svg>

        <!-- Refresh/circular arrows icon -->
        <svg v-else-if="item.icon === 'refresh'" class="nav-icon" viewBox="0 0 18 18" fill="none" xmlns="http://www.w3.org/2000/svg" aria-hidden="true">
          <path d="M1 9a8 8 0 0 1 13.66-5.66L17 1" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/>
          <path d="M17 1v5h-5" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/>
          <path d="M17 9a8 8 0 0 1-13.66 5.66L1 17" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/>
          <path d="M1 17v-5h5" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/>
        </svg>

        <span class="nav-label">{{ item.label }}</span>
      </router-link>
    </div>

    <!-- Footer Section -->
    <div class="sidebar-footer">
      <div class="user-section">
        <div class="user-avatar" :title="currentUser.name">
          {{ getInitials(currentUser.name) }}
        </div>
        <div class="user-info">
          <span class="user-name">{{ currentUser.name }}</span>
          <span class="user-email">{{ currentUser.email }}</span>
        </div>
      </div>
      <div class="footer-actions">
        <button class="footer-btn" @click="handleShowTasks" :title="isCollapsed ? 'My Tasks' : ''">
          <!-- Task icon shown in collapsed state -->
          <svg class="footer-btn-icon" viewBox="0 0 18 18" fill="none" xmlns="http://www.w3.org/2000/svg" aria-hidden="true">
            <rect x="3" y="3" width="12" height="14" rx="1.5" stroke="currentColor" stroke-width="1.5" fill="none"/>
            <path d="M6 7h6M6 10h6M6 13h3" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/>
          </svg>
          <span class="footer-btn-label">
            My Tasks
            <span v-if="pendingTaskCount > 0" class="task-badge">{{ pendingTaskCount }}</span>
          </span>
        </button>
        <button class="footer-btn" @click="handleShowProfile" :title="isCollapsed ? 'Profile Details' : ''">
          <!-- Person icon shown in collapsed state -->
          <svg class="footer-btn-icon" viewBox="0 0 18 18" fill="none" xmlns="http://www.w3.org/2000/svg" aria-hidden="true">
            <circle cx="9" cy="6" r="3.5" stroke="currentColor" stroke-width="1.5" fill="none"/>
            <path d="M1.5 16.5c0-3.314 3.358-6 7.5-6s7.5 2.686 7.5 6" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" fill="none"/>
          </svg>
          <span class="footer-btn-label">Profile Details</span>
        </button>
      </div>
    </div>
  </nav>
</template>

<script>
import { ref, computed, onMounted, onBeforeUnmount } from 'vue'
import { useRoute } from 'vue-router'
import { useAuth } from '../composables/useAuth'
import { useI18n } from '../composables/useI18n'

const STORAGE_KEY = 'sidebarCollapsed'
const MOBILE_BREAKPOINT = 768

export default {
  name: 'Sidebar',
  emits: ['show-profile-details', 'show-tasks', 'collapse-change'],
  setup(props, { emit }) {
    const route = useRoute()
    const { currentUser, getInitials } = useAuth()
    const { t } = useI18n()

    // Initialise from localStorage; fall back to mobile-breakpoint default.
    // Reading window.innerWidth during setup is safe because the component
    // mounts after the DOM is available.
    const getInitialCollapsed = () => {
      const stored = localStorage.getItem(STORAGE_KEY)
      if (stored !== null) return stored === 'true'
      return window.innerWidth < MOBILE_BREAKPOINT
    }

    const isCollapsed = ref(getInitialCollapsed())

    const toggleSidebar = () => {
      isCollapsed.value = !isCollapsed.value
      localStorage.setItem(STORAGE_KEY, String(isCollapsed.value))
      emit('collapse-change', isCollapsed.value)
    }

    // Collapse automatically when viewport drops below the mobile breakpoint.
    // We only auto-collapse (never auto-expand) to avoid overriding an
    // explicit user choice to keep the sidebar open on a small window.
    const handleResize = () => {
      if (window.innerWidth < MOBILE_BREAKPOINT && !isCollapsed.value) {
        isCollapsed.value = true
        localStorage.setItem(STORAGE_KEY, 'true')
        emit('collapse-change', true)
      }
    }

    onMounted(() => {
      window.addEventListener('resize', handleResize)
      // Notify parent of initial state so App.vue can set layout correctly
      emit('collapse-change', isCollapsed.value)
    })

    onBeforeUnmount(() => {
      window.removeEventListener('resize', handleResize)
    })

    const navItems = computed(() => [
      { path: '/', label: t('nav.overview'), icon: 'home' },
      { path: '/inventory', label: t('nav.inventory'), icon: 'box' },
      { path: '/orders', label: t('nav.orders'), icon: 'clipboard' },
      { path: '/spending', label: t('nav.finance'), icon: 'dollar' },
      { path: '/demand', label: t('nav.demandForecast'), icon: 'chart' },
      { path: '/reports', label: 'Reports', icon: 'document' },
      { path: '/restocking', label: 'Restocking', icon: 'refresh' }
    ])

    const pendingTaskCount = computed(() =>
      currentUser.value.tasks.filter(task => task.status === 'pending').length
    )

    const isActive = (path) => route.path === path

    const handleShowTasks = () => emit('show-tasks')
    const handleShowProfile = () => emit('show-profile-details')

    return {
      navItems,
      currentUser,
      getInitials,
      pendingTaskCount,
      isActive,
      isCollapsed,
      toggleSidebar,
      t,
      handleShowTasks,
      handleShowProfile
    }
  }
}
</script>

<style scoped>
/* ─── Width variables ──────────────────────────────────────────────────── */
.sidebar {
  --sidebar-width: 260px;
  --sidebar-collapsed-width: 80px;

  width: var(--sidebar-width);
  min-width: var(--sidebar-width);
  height: 100vh;
  background: #0f172a;
  display: flex;
  flex-direction: column;
  border-right: 1px solid rgba(255, 255, 255, 0.1);
  position: sticky;
  top: 0;
  overflow: hidden;
  /* Transition width and min-width together for a smooth collapse */
  transition: width 0.25s ease, min-width 0.25s ease;
}

.sidebar.collapsed {
  width: var(--sidebar-collapsed-width);
  min-width: var(--sidebar-collapsed-width);
}

/* ─── Brand ────────────────────────────────────────────────────────────── */
.sidebar-brand {
  padding: 1.25rem 1rem;
  border-bottom: 1px solid rgba(255, 255, 255, 0.1);
  flex-shrink: 0;
  /* Stack brand content and the toggle button */
  display: flex;
  flex-direction: column;
  gap: 0.375rem;
  position: relative;
}

.brand-logo {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  margin-bottom: 0.25rem;
  overflow: hidden;
}

.brand-icon {
  flex-shrink: 0;
}

.brand-name {
  color: #ffffff;
  font-weight: 700;
  font-size: 1rem;
  letter-spacing: -0.01em;
  white-space: nowrap;
  /* Fade out the text when collapsing */
  opacity: 1;
  transition: opacity 0.15s ease;
}

.sidebar.collapsed .brand-name {
  opacity: 0;
  pointer-events: none;
}

.brand-subtitle {
  color: #94a3b8;
  font-size: 0.75rem;
  line-height: 1.4;
  padding-left: 0.25rem;
  white-space: nowrap;
  overflow: hidden;
  opacity: 1;
  transition: opacity 0.15s ease;
}

.sidebar.collapsed .brand-subtitle {
  opacity: 0;
  pointer-events: none;
}

/* Toggle button */
.toggle-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 28px;
  height: 28px;
  background: rgba(255, 255, 255, 0.07);
  border: 1px solid rgba(255, 255, 255, 0.15);
  border-radius: 6px;
  color: #94a3b8;
  cursor: pointer;
  transition: background 0.2s ease, color 0.2s ease, border-color 0.2s ease;
  /* When expanded the button sits at the bottom of the brand block.
     When collapsed we want it centred over the icon. */
  align-self: flex-start;
  margin-top: 0.25rem;
}

.sidebar.collapsed .toggle-btn {
  /* Centre the toggle under the brand logo in icon-only mode */
  align-self: center;
  margin-top: 0;
}

.toggle-btn:hover {
  background: rgba(255, 255, 255, 0.14);
  color: #e2e8f0;
  border-color: rgba(255, 255, 255, 0.25);
}

.toggle-btn svg {
  width: 14px;
  height: 14px;
  flex-shrink: 0;
}

/* ─── Navigation ───────────────────────────────────────────────────────── */
.sidebar-nav {
  flex: 1;
  overflow-y: auto;
  overflow-x: hidden;
  padding: 0.5rem 0.5rem;
  scrollbar-width: thin;
  scrollbar-color: rgba(255, 255, 255, 0.1) transparent;
}

.sidebar-nav::-webkit-scrollbar {
  width: 4px;
}

.sidebar-nav::-webkit-scrollbar-track {
  background: transparent;
}

.sidebar-nav::-webkit-scrollbar-thumb {
  background: rgba(255, 255, 255, 0.1);
  border-radius: 2px;
}

.nav-item {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  padding: 0.75rem 0.875rem;
  margin: 0.25rem 0;
  border-radius: 8px;
  color: #94a3b8;
  text-decoration: none;
  font-size: 0.875rem;
  font-weight: 500;
  transition: background 0.2s ease, color 0.2s ease, padding 0.25s ease;
  position: relative;
  border-left: 3px solid transparent;
  cursor: pointer;
  white-space: nowrap;
  overflow: hidden;
}

/* Centre the icon and remove the left-border highlight when collapsed */
.sidebar.collapsed .nav-item {
  padding: 0.75rem 0;
  justify-content: center;
  border-left-color: transparent !important;
}

.sidebar.collapsed .nav-item.active {
  /* Keep active background but replace border indicator with a subtle ring */
  background: rgba(37, 99, 235, 0.15);
  color: #60a5fa;
}

.nav-item:hover {
  background: rgba(255, 255, 255, 0.05);
  color: #e2e8f0;
}

.nav-item.active {
  background: rgba(37, 99, 235, 0.15);
  color: #60a5fa;
  border-left-color: #2563eb;
}

.nav-item.active .nav-icon {
  color: #60a5fa;
}

.nav-icon {
  width: 18px;
  height: 18px;
  flex-shrink: 0;
  color: inherit;
  /* Slightly larger icon in collapsed mode — handled via transform */
  transition: transform 0.25s ease;
}

.sidebar.collapsed .nav-icon {
  transform: scale(1.15);
}

.nav-label {
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  opacity: 1;
  transition: opacity 0.15s ease;
}

.sidebar.collapsed .nav-label {
  opacity: 0;
  width: 0;
  pointer-events: none;
}

/* ─── Footer ───────────────────────────────────────────────────────────── */
.sidebar-footer {
  padding: 1rem;
  border-top: 1px solid rgba(255, 255, 255, 0.1);
  flex-shrink: 0;
  overflow: hidden;
}

.user-section {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  margin-bottom: 0.875rem;
  overflow: hidden;
}

.sidebar.collapsed .user-section {
  justify-content: center;
  margin-bottom: 0.5rem;
}

.user-avatar {
  width: 36px;
  height: 36px;
  border-radius: 50%;
  background: linear-gradient(135deg, #2563eb, #1e40af);
  color: #ffffff;
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: 600;
  font-size: 0.875rem;
  flex-shrink: 0;
  user-select: none;
}

.user-info {
  display: flex;
  flex-direction: column;
  gap: 0.125rem;
  min-width: 0;
  flex: 1;
  opacity: 1;
  transition: opacity 0.15s ease;
}

.sidebar.collapsed .user-info {
  opacity: 0;
  width: 0;
  pointer-events: none;
}

.user-name {
  color: #ffffff;
  font-size: 0.875rem;
  font-weight: 600;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.user-email {
  color: #94a3b8;
  font-size: 0.75rem;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.footer-actions {
  display: flex;
  gap: 0.5rem;
}

.sidebar.collapsed .footer-actions {
  flex-direction: column;
  align-items: center;
  gap: 0.375rem;
}

.footer-btn {
  flex: 1;
  padding: 0.5rem 0.5rem;
  background: transparent;
  border: 1px solid rgba(255, 255, 255, 0.2);
  color: #ffffff;
  border-radius: 6px;
  cursor: pointer;
  font-size: 0.75rem;
  font-weight: 600;
  transition: background 0.2s ease, border-color 0.2s ease;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 0.375rem;
  overflow: hidden;
  font-family: inherit;
}

.sidebar.collapsed .footer-btn {
  flex: none;
  width: 42px;
  height: 34px;
  padding: 0;
}

.footer-btn:hover {
  background: rgba(255, 255, 255, 0.1);
  border-color: rgba(255, 255, 255, 0.3);
}

.footer-btn-icon {
  width: 15px;
  height: 15px;
  flex-shrink: 0;
}

.footer-btn-label {
  display: flex;
  align-items: center;
  gap: 0.375rem;
  white-space: nowrap;
  opacity: 1;
  transition: opacity 0.15s ease;
}

.sidebar.collapsed .footer-btn-label {
  opacity: 0;
  width: 0;
  pointer-events: none;
}

.task-badge {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  background: #dc2626;
  color: #ffffff;
  border-radius: 50%;
  width: 18px;
  height: 18px;
  font-size: 0.65rem;
  font-weight: 700;
  flex-shrink: 0;
  line-height: 1;
}

/* ─── Responsive: force collapse on small screens ──────────────────────── */
@media (max-width: 767px) {
  .sidebar {
    width: var(--sidebar-collapsed-width);
    min-width: var(--sidebar-collapsed-width);
  }
}
</style>
