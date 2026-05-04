<script setup>
import { useI18n } from '../composables/useI18n'
import { formatCurrency } from '../utils/currency'

defineProps({
  topProducts: { type: Array, required: true }
})

const emit = defineEmits(['show-detail'])

const { t, currentCurrency, translateProductName, translateCategory } = useI18n()

const getStockBadge = (level) => {
  if (level === 'In Stock') return 'success'
  if (level === 'Low Stock') return 'warning'
  return 'danger'
}

const translateStockLevel = (stockLevel) => {
  const map = { 'In Stock': t('status.inStock'), 'Low Stock': t('status.lowStock') }
  return map[stockLevel] || stockLevel
}

const formatDate = (dateString) => {
  if (!dateString) return '-'
  const { currentLocale } = useI18n()
  const locale = currentLocale.value === 'ja' ? 'ja-JP' : 'en-US'
  const date = new Date(dateString)
  return isNaN(date.getTime()) ? '-' : date.toLocaleDateString(locale, { month: 'short', day: 'numeric', year: 'numeric' })
}
</script>

<template>
  <div class="card">
    <div class="card-header">
      <h3 class="card-title">{{ t('dashboard.topProducts.title') }}</h3>
    </div>
    <div class="table-container">
      <table>
        <thead>
          <tr>
            <th>{{ t('dashboard.topProducts.product') }}</th>
            <th>{{ t('dashboard.topProducts.sku') }}</th>
            <th>{{ t('dashboard.topProducts.category') }}</th>
            <th>{{ t('dashboard.topProducts.unitsOrdered') }}</th>
            <th>{{ t('dashboard.topProducts.revenue') }}</th>
            <th>{{ t('dashboard.topProducts.firstOrder') }}</th>
            <th>{{ t('dashboard.topProducts.stockStatus') }}</th>
          </tr>
        </thead>
        <tbody>
          <tr
            v-for="item in topProducts"
            :key="item.sku"
            class="clickable-row"
            @click="emit('show-detail', item)"
          >
            <td><strong>{{ translateProductName(item.name) }}</strong></td>
            <td>{{ item.sku }}</td>
            <td>{{ translateCategory(item.category) }}</td>
            <td>{{ item.unitsOrdered }}</td>
            <td><strong>{{ formatCurrency(item.revenue, currentCurrency) }}</strong></td>
            <td>{{ formatDate(item.firstOrderDate) }}</td>
            <td>
              <span :class="['badge', getStockBadge(item.stockLevel)]">
                {{ translateStockLevel(item.stockLevel) }}
              </span>
            </td>
          </tr>
        </tbody>
      </table>
    </div>
  </div>
</template>

<style scoped>
.clickable-row {
  cursor: pointer;
  transition: background-color 0.15s ease;
}

.clickable-row:hover {
  background: #eff6ff !important;
}
</style>
