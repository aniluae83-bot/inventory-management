<template>
  <div class="restocking">
    <div class="page-header">
      <h2>Restocking Planner</h2>
      <p>Set your available budget to get demand-based restocking recommendations. Items are prioritized by the largest gap between forecasted and current demand.</p>
    </div>

    <div v-if="loading" class="loading">Loading demand data...</div>
    <div v-else-if="error" class="error">{{ error }}</div>
    <div v-else>

      <!-- Budget Slider Card -->
      <div class="card">
        <div class="card-header">
          <h3 class="card-title">Available Budget</h3>
          <div class="budget-display">
            <span class="budget-amount">${{ Math.round(budget).toLocaleString() }}</span>
            <span class="budget-pill" :class="remainingBudget >= 0 ? 'pill-green' : 'pill-red'">
              ${{ Math.round(remainingBudget).toLocaleString() }} remaining
            </span>
          </div>
        </div>
        <input
          type="range"
          v-model.number="budget"
          :min="0"
          :max="Math.ceil(totalCost)"
          :step="1000"
          class="budget-slider"
        />
        <div class="slider-labels">
          <span>$0</span>
          <span>${{ Math.ceil(totalCost).toLocaleString() }} (all items)</span>
        </div>
      </div>

      <!-- Recommendations Table -->
      <div class="card">
        <div class="card-header">
          <h3 class="card-title">Demand-Based Recommendations</h3>
          <span class="badge info">{{ recommendedItems.length }} of {{ sortedItems.length }} items selected</span>
        </div>
        <div class="table-container">
          <table>
            <thead>
              <tr>
                <th>SKU</th>
                <th>Item Name</th>
                <th>Trend</th>
                <th>Demand Gap</th>
                <th>Restock Qty</th>
                <th>Unit Cost</th>
                <th>Total Cost</th>
                <th>Status</th>
              </tr>
            </thead>
            <tbody>
              <tr
                v-for="item in sortedItems"
                :key="item.id"
                :class="isSelected(item) ? 'row-selected' : 'row-excluded'"
              >
                <td><strong>{{ item.item_sku }}</strong></td>
                <td>{{ item.item_name }}</td>
                <td><span :class="['badge', item.trend]">{{ item.trend }}</span></td>
                <td :class="item.demand_gap > 0 ? 'gap-positive' : item.demand_gap < 0 ? 'gap-negative' : ''">
                  {{ item.demand_gap > 0 ? '+' : '' }}{{ item.demand_gap.toLocaleString() }}
                </td>
                <td>{{ item.forecasted_demand.toLocaleString() }}</td>
                <td>${{ item.unit_cost.toFixed(2) }}</td>
                <td><strong>${{ Math.round(item.restock_cost).toLocaleString() }}</strong></td>
                <td>
                  <span v-if="isSelected(item)" class="badge success">Selected</span>
                  <span v-else class="badge excluded-badge">Over budget</span>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>

      <!-- Order Summary + Place Order -->
      <div class="card summary-card">
        <div class="card-header">
          <h3 class="card-title">Order Summary</h3>
        </div>
        <div class="summary-grid">
          <div class="summary-item">
            <span class="summary-label">Items to Restock</span>
            <span class="summary-value" :class="recommendedItems.length === 0 ? 'value-muted' : ''">
              {{ recommendedItems.length }}
            </span>
          </div>
          <div class="summary-item">
            <span class="summary-label">Total Cost</span>
            <span class="summary-value">${{ Math.round(selectedTotalCost).toLocaleString() }}</span>
          </div>
          <div class="summary-item">
            <span class="summary-label">Expected Delivery</span>
            <span class="summary-value">{{ expectedDeliveryDate }}</span>
          </div>
          <div class="summary-item">
            <span class="summary-label">Lead Time</span>
            <span class="summary-value">14 days</span>
          </div>
        </div>
        <div class="order-actions">
          <button
            @click="placeOrder"
            :disabled="placing || recommendedItems.length === 0"
            class="place-order-btn"
          >
            {{ placing ? 'Placing Order...' : 'Place Order' }}
          </button>
          <span v-if="recommendedItems.length === 0" class="no-items-hint">
            Increase the budget slider to select items for restocking.
          </span>
        </div>
      </div>

      <!-- Success Banner -->
      <div v-if="successOrder" class="success-banner">
        Order <strong>{{ successOrder.order_number }}</strong> placed successfully — {{ successOrder.items.length }} items, ${{ Math.round(successOrder.total_value).toLocaleString() }} total. Expected delivery: {{ formatDate(successOrder.expected_delivery) }}. View it in the Orders tab.
      </div>

    </div>
  </div>
</template>

<script>
import { ref, computed, onMounted, watch } from 'vue'
import { api } from '../api'

export default {
  name: 'Restocking',
  setup() {
    const loading = ref(true)
    const error = ref(null)
    const placing = ref(false)
    const successOrder = ref(null)

    const forecasts = ref([])
    const inventoryItems = ref([])
    const budget = ref(0)

    // Cross-reference demand forecasts with inventory to get unit_cost per item
    const enrichedItems = computed(() => {
      return forecasts.value.map(forecast => {
        const inventoryItem = inventoryItems.value.find(inv => inv.sku === forecast.item_sku)
        // Fallback unit cost when no inventory match found
        const unit_cost = inventoryItem ? inventoryItem.unit_cost : 50
        const demand_gap = forecast.forecasted_demand - forecast.current_demand
        const restock_cost = forecast.forecasted_demand * unit_cost
        return { ...forecast, unit_cost, demand_gap, restock_cost }
      })
    })

    // Sort by demand gap descending — biggest unmet demand first
    const sortedItems = computed(() => {
      return [...enrichedItems.value].sort((a, b) => b.demand_gap - a.demand_gap)
    })

    // Total cost if every item were restocked
    const totalCost = computed(() => {
      return enrichedItems.value.reduce((sum, item) => sum + item.restock_cost, 0)
    })

    // Greedy selection: walk sorted list, pick item if it fits in remaining budget
    const recommendedItems = computed(() => {
      const selected = []
      let running = 0
      for (const item of sortedItems.value) {
        if (running + item.restock_cost <= budget.value) {
          selected.push(item)
          running += item.restock_cost
        }
      }
      return selected
    })

    const selectedTotalCost = computed(() => {
      return recommendedItems.value.reduce((sum, item) => sum + item.restock_cost, 0)
    })

    const remainingBudget = computed(() => budget.value - selectedTotalCost.value)

    const isSelected = (item) => recommendedItems.value.some(r => r.id === item.id)

    const expectedDeliveryDate = computed(() => {
      const date = new Date()
      date.setDate(date.getDate() + 14)
      return date.toLocaleDateString('en-US', { year: 'numeric', month: 'short', day: 'numeric' })
    })

    const formatDate = (dateString) => {
      return new Date(dateString).toLocaleDateString('en-US', {
        year: 'numeric', month: 'short', day: 'numeric'
      })
    }

    const placeOrder = async () => {
      if (recommendedItems.value.length === 0 || placing.value) return
      try {
        placing.value = true
        error.value = null
        successOrder.value = null
        const result = await api.createRestockingOrder({
          items: recommendedItems.value.map(item => ({
            sku: item.item_sku,
            name: item.item_name,
            quantity: item.forecasted_demand,
            unit_cost: item.unit_cost,
            total_cost: item.restock_cost
          })),
          budget: budget.value,
          total_value: selectedTotalCost.value
        })
        successOrder.value = result
      } catch (err) {
        error.value = 'Failed to place order: ' + err.message
      } finally {
        placing.value = false
      }
    }

    const loadData = async () => {
      try {
        loading.value = true
        const [forecastsData, inventoryData] = await Promise.all([
          api.getDemandForecasts(),
          api.getInventory({})
        ])
        forecasts.value = forecastsData
        inventoryItems.value = inventoryData
      } catch (err) {
        error.value = 'Failed to load data: ' + err.message
      } finally {
        loading.value = false
      }
    }

    // Set default budget to ~half of total once data loads
    watch(totalCost, (newVal) => {
      if (budget.value === 0 && newVal > 0) {
        budget.value = Math.round(newVal * 0.5 / 1000) * 1000
      }
    })

    onMounted(loadData)

    return {
      loading,
      error,
      placing,
      successOrder,
      budget,
      sortedItems,
      totalCost,
      recommendedItems,
      selectedTotalCost,
      remainingBudget,
      isSelected,
      expectedDeliveryDate,
      formatDate,
      placeOrder
    }
  }
}
</script>

<style scoped>
/* Budget slider */
.budget-display {
  display: flex;
  align-items: center;
  gap: 0.75rem;
}

.budget-amount {
  font-size: 1.75rem;
  font-weight: 700;
  color: #0f172a;
  letter-spacing: -0.025em;
}

.budget-pill {
  display: inline-block;
  font-size: 0.813rem;
  font-weight: 600;
  padding: 0.25rem 0.875rem;
  border-radius: 20px;
}

.pill-green {
  background: #d1fae5;
  color: #065f46;
}

.pill-red {
  background: #fecaca;
  color: #991b1b;
}

.budget-slider {
  width: 100%;
  height: 6px;
  accent-color: #3b82f6;
  cursor: pointer;
  margin-top: 0.5rem;
}

.slider-labels {
  display: flex;
  justify-content: space-between;
  margin-top: 0.5rem;
  font-size: 0.813rem;
  color: #64748b;
}

/* Table row states */
.row-selected {
  background: #f0f9ff;
}

.row-selected:hover {
  background: #e0f2fe !important;
}

.row-excluded {
  opacity: 0.45;
}

.row-excluded:hover {
  background: #f8fafc !important;
}

.gap-positive {
  color: #059669;
  font-weight: 600;
}

.gap-negative {
  color: #dc2626;
  font-weight: 600;
}

.excluded-badge {
  background: #f1f5f9;
  color: #94a3b8;
  display: inline-block;
  padding: 0.313rem 0.75rem;
  border-radius: 6px;
  font-size: 0.75rem;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.025em;
}

/* Order Summary */
.summary-card {
  margin-bottom: 1rem;
}

.summary-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 1.5rem;
  margin-bottom: 1.5rem;
}

.summary-item {
  display: flex;
  flex-direction: column;
  gap: 0.375rem;
}

.summary-label {
  font-size: 0.75rem;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  color: #64748b;
}

.summary-value {
  font-size: 1.5rem;
  font-weight: 700;
  color: #0f172a;
  letter-spacing: -0.025em;
}

.value-muted {
  color: #94a3b8;
}

.order-actions {
  display: flex;
  align-items: center;
  gap: 1rem;
}

.place-order-btn {
  background: #3b82f6;
  color: white;
  border: none;
  padding: 0.75rem 2rem;
  border-radius: 8px;
  font-size: 0.938rem;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s ease;
  white-space: nowrap;
}

.place-order-btn:hover:not(:disabled) {
  background: #2563eb;
  transform: translateY(-1px);
  box-shadow: 0 4px 12px rgba(37, 99, 235, 0.3);
}

.place-order-btn:disabled {
  opacity: 0.45;
  cursor: not-allowed;
  transform: none;
  box-shadow: none;
}

.no-items-hint {
  font-size: 0.875rem;
  color: #64748b;
}

/* Success Banner */
.success-banner {
  background: #d1fae5;
  border: 1px solid #6ee7b7;
  color: #065f46;
  padding: 1rem 1.25rem;
  border-radius: 8px;
  font-size: 0.938rem;
  line-height: 1.5;
}
</style>
