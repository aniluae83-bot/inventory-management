<script setup>
import { computed } from 'vue'
import { useI18n } from '../composables/useI18n'
import { formatCurrency } from '../utils/currency'

const props = defineProps({
  statusData:         { type: Object, required: true },
  orderHealthMetrics: { type: Object, required: true }
})

const { t, currentCurrency } = useI18n()

const totalOrders = computed(() =>
  props.statusData.delivered + props.statusData.shipped +
  props.statusData.processing + props.statusData.backordered
)

const getCircleSegment = (value) =>
  totalOrders.value > 0 ? (value / totalOrders.value) * 440 : 0
</script>

<template>
  <div class="card chart-card">
    <div class="card-header">
      <h3 class="card-title">{{ t('dashboard.orderHealth.title') }}</h3>
    </div>
    <div class="chart-content">
      <div class="order-health-container">
        <div class="order-health-chart">
          <svg viewBox="0 0 200 200" class="donut-svg-compact">
            <circle cx="100" cy="100" r="65" fill="none" stroke="#e2e8f0" stroke-width="25"/>
            <circle cx="100" cy="100" r="65" fill="none" stroke="#10b981" stroke-width="25"
              :stroke-dasharray="`${getCircleSegment(statusData.delivered)} 408`"
              stroke-dashoffset="0" transform="rotate(-90 100 100)"/>
            <circle cx="100" cy="100" r="65" fill="none" stroke="#3b82f6" stroke-width="25"
              :stroke-dasharray="`${getCircleSegment(statusData.shipped)} 408`"
              :stroke-dashoffset="`-${getCircleSegment(statusData.delivered)}`"
              transform="rotate(-90 100 100)"/>
            <circle cx="100" cy="100" r="65" fill="none" stroke="#f59e0b" stroke-width="25"
              :stroke-dasharray="`${getCircleSegment(statusData.processing)} 408`"
              :stroke-dashoffset="`-${getCircleSegment(statusData.delivered) + getCircleSegment(statusData.shipped)}`"
              transform="rotate(-90 100 100)"/>
            <circle cx="100" cy="100" r="65" fill="none" stroke="#ef4444" stroke-width="25"
              :stroke-dasharray="`${getCircleSegment(statusData.backordered)} 408`"
              :stroke-dashoffset="`-${getCircleSegment(statusData.delivered) + getCircleSegment(statusData.shipped) + getCircleSegment(statusData.processing)}`"
              transform="rotate(-90 100 100)"/>
            <text x="100" y="90" text-anchor="middle" class="donut-center-label">{{ t('dashboard.orderHealth.total') }}</text>
            <text x="100" y="120" text-anchor="middle" class="donut-center-value">{{ orderHealthMetrics.totalOrders }}</text>
          </svg>
          <div class="donut-legend-compact">
            <div class="legend-item-compact"><span class="legend-dot" style="background: #10b981"></span>{{ t('status.delivered') }}</div>
            <div class="legend-item-compact"><span class="legend-dot" style="background: #3b82f6"></span>{{ t('status.shipped') }}</div>
            <div class="legend-item-compact"><span class="legend-dot" style="background: #f59e0b"></span>{{ t('status.processing') }}</div>
            <div class="legend-item-compact"><span class="legend-dot" style="background: #ef4444"></span>{{ t('status.backordered') }}</div>
          </div>
        </div>

        <div class="order-health-metrics">
          <div class="health-metric">
            <div class="health-metric-label">{{ t('dashboard.orderHealth.revenue') }}</div>
            <div class="health-metric-value">{{ formatCurrency(orderHealthMetrics.totalValue, currentCurrency) }}</div>
          </div>
          <div class="health-metric">
            <div class="health-metric-label">{{ t('dashboard.orderHealth.avgOrderValue') }}</div>
            <div class="health-metric-value">{{ formatCurrency(orderHealthMetrics.avgOrderValue, currentCurrency) }}</div>
          </div>
          <div class="health-metric">
            <div class="health-metric-label">{{ t('dashboard.orderHealth.onTimeRate') }}</div>
            <div class="health-metric-value"
              :class="{
                'metric-good':    orderHealthMetrics.onTimeRate >= 90,
                'metric-warning': orderHealthMetrics.onTimeRate < 90 && orderHealthMetrics.onTimeRate >= 75,
                'metric-bad':     orderHealthMetrics.onTimeRate < 75
              }">
              {{ orderHealthMetrics.onTimeRate.toFixed(1) }}%
            </div>
          </div>
          <div class="health-metric">
            <div class="health-metric-label">{{ t('dashboard.orderHealth.avgFulfillmentDays') }}</div>
            <div class="health-metric-value">{{ orderHealthMetrics.avgFulfillmentDays.toFixed(1) }}</div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.chart-content {
  padding: 1rem;
}

.order-health-container {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 1.5rem;
  align-items: center;
  padding: 1rem;
  min-height: 240px;
}

.order-health-chart {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 1rem;
  padding: 0 1rem;
}

.donut-svg-compact {
  width: 200px;
  height: 200px;
}

.donut-center-label {
  font-size: 12px;
  fill: #64748b;
  font-weight: 500;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.donut-center-value {
  font-size: 36px;
  fill: #0f172a;
  font-weight: 700;
}

.donut-legend-compact {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 0.625rem 1.25rem;
}

.legend-item-compact {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  font-size: 0.875rem;
  color: #475569;
  font-weight: 500;
}

.legend-dot {
  width: 10px;
  height: 10px;
  border-radius: 2px;
}

.order-health-metrics {
  display: flex;
  flex-direction: column;
  gap: 1.25rem;
  justify-content: center;
  align-items: center;
}

.health-metric {
  display: flex;
  flex-direction: column;
  gap: 0.375rem;
  text-align: center;
  width: 100%;
}

.health-metric-label {
  font-size: 0.688rem;
  color: #64748b;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

.health-metric-value {
  font-size: 1.75rem;
  font-weight: 700;
  color: #0f172a;
  letter-spacing: -0.025em;
}

.metric-good    { color: #10b981; }
.metric-warning { color: #f59e0b; }
.metric-bad     { color: #ef4444; }
</style>
