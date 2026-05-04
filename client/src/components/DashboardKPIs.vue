<script setup>
import { useI18n } from '../composables/useI18n'
import { formatCurrency } from '../utils/currency'

const props = defineProps({
  ordersData:    { type: Object, required: true },
  fillRate:      { type: Number, required: true },
  summary:       { type: Object, required: true },
  revenueGoal:   { type: Number, required: true },
  selectedPeriod:{ type: String, required: true }
})

const { t, currentCurrency } = useI18n()

const calculatePercentage = (value, goal) => ((value / goal) * 100).toFixed(2)
</script>

<template>
  <div class="kpi-section">
    <h3 class="section-title">{{ t('dashboard.kpi.title') }}</h3>
    <div class="kpi-grid">
      <div class="kpi-card">
        <div class="kpi-header">
          <span class="kpi-label">{{ t('dashboard.kpi.inventoryTurnover') }}</span>
        </div>
        <div class="kpi-value">4.2</div>
        <div class="kpi-goal">{{ t('dashboard.kpi.goal') }}: 4.5 (-6.67%)</div>
        <div class="kpi-progress-bar"><div class="kpi-progress" style="width: 93.33%"></div></div>
      </div>

      <div class="kpi-card">
        <div class="kpi-header">
          <span class="kpi-label">{{ t('dashboard.kpi.ordersFulfilled') }}</span>
        </div>
        <div class="kpi-value">{{ ordersData.fulfilled }}</div>
        <div class="kpi-goal">{{ t('dashboard.kpi.goal') }}: {{ ordersData.goal }} ({{ calculatePercentage(ordersData.fulfilled, ordersData.goal) }}%)</div>
        <div class="kpi-progress-bar">
          <div class="kpi-progress" :style="{ width: calculatePercentage(ordersData.fulfilled, ordersData.goal) + '%' }"></div>
        </div>
      </div>

      <div class="kpi-card">
        <div class="kpi-header">
          <span class="kpi-label">{{ t('dashboard.kpi.orderFillRate') }}</span>
        </div>
        <div class="kpi-value">{{ fillRate }}%</div>
        <div class="kpi-goal">{{ t('dashboard.kpi.goal') }}: 95% ({{ fillRate - 95 > 0 ? '+' : '' }}{{ (fillRate - 95).toFixed(2) }}%)</div>
        <div class="kpi-progress-bar">
          <div class="kpi-progress success" :style="{ width: (fillRate / 95 * 100) + '%' }"></div>
        </div>
      </div>

      <div class="kpi-card">
        <div class="kpi-header">
          <span class="kpi-label">{{ t(selectedPeriod === 'all' ? 'dashboard.kpi.revenueYTD' : 'dashboard.kpi.revenueMTD') }}</span>
        </div>
        <div class="kpi-value">{{ formatCurrency(Math.round(summary.total_orders_value), currentCurrency) }}</div>
        <div class="kpi-goal">
          {{ t('dashboard.kpi.goal') }}: {{ formatCurrency(revenueGoal, currentCurrency) }}
          ({{ summary.total_orders_value > revenueGoal ? '+' : '' }}{{ ((summary.total_orders_value / revenueGoal - 1) * 100).toFixed(1) }}%)
        </div>
        <div class="kpi-progress-bar">
          <div class="kpi-progress" :style="{ width: Math.min((summary.total_orders_value / revenueGoal * 100), 100) + '%' }"></div>
        </div>
      </div>

      <div class="kpi-card">
        <div class="kpi-header">
          <span class="kpi-label">{{ t('dashboard.kpi.avgProcessingTime') }}</span>
        </div>
        <div class="kpi-value">2.8</div>
        <div class="kpi-goal">{{ t('dashboard.kpi.goal') }}: 3.0 (-6.67%)</div>
        <div class="kpi-progress-bar"><div class="kpi-progress success" style="width: 93.33%"></div></div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.kpi-section {
  margin-bottom: 1.5rem;
}

.section-title {
  font-size: 1rem;
  font-weight: 600;
  color: #475569;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  margin-bottom: 1rem;
}

.kpi-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
  gap: 1rem;
}

.kpi-card {
  background: white;
  border: 1px solid #e2e8f0;
  border-radius: 10px;
  padding: 1rem;
}

.kpi-header {
  margin-bottom: 0.75rem;
}

.kpi-label {
  font-size: 0.813rem;
  font-weight: 600;
  color: #64748b;
  text-transform: uppercase;
  letter-spacing: 0.025em;
}

.kpi-value {
  font-size: 2rem;
  font-weight: 700;
  color: #0f172a;
  margin-bottom: 0.5rem;
  letter-spacing: -0.025em;
}

.kpi-goal {
  font-size: 0.813rem;
  color: #64748b;
  margin-bottom: 0.75rem;
}

.kpi-progress-bar {
  width: 100%;
  height: 6px;
  background: #f1f5f9;
  border-radius: 3px;
  overflow: hidden;
}

.kpi-progress {
  height: 100%;
  background: #3b82f6;
  border-radius: 3px;
  transition: width 0.6s ease;
}

.kpi-progress.success {
  background: #10b981;
}
</style>
