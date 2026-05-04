<template>
  <div class="restocking">
    <div class="page-header">
      <h2>Restocking</h2>
      <p>Build a restocking order based on budget</p>
    </div>

    <div v-if="loading" class="loading">{{ t('common.loading') }}</div>
    <div v-else-if="error" class="error">{{ error }}</div>
    <div v-else>

      <!-- Success Banner -->
      <div v-if="successMessage" class="success-banner">
        <span class="success-icon">&#10003;</span>
        {{ successMessage }}
      </div>

      <!-- Budget Slider Card -->
      <div class="card">
        <div class="card-header">
          <h3 class="card-title">Budget</h3>
          <span class="budget-display">{{ formatCurrency(budget) }}</span>
        </div>
        <div class="slider-section">
          <div class="slider-labels">
            <span>{{ formatCurrency(0) }}</span>
            <span>{{ formatCurrency(100000) }}</span>
          </div>
          <input
            type="range"
            min="0"
            max="100000"
            step="1000"
            v-model.number="budget"
            class="budget-slider"
          />
          <div class="slider-hint">
            Drag to set available budget. Step: {{ formatCurrency(1000) }}.
          </div>
        </div>
      </div>

      <!-- Recommendations Table Card -->
      <div class="card">
        <div class="card-header">
          <h3 class="card-title">
            Recommended Items to Restock
            <span v-if="recommendations.length > 0" class="item-count-badge">
              {{ recommendations.length }}
            </span>
          </h3>
          <div class="budget-summary" v-if="recommendations.length > 0">
            <span class="budget-used">
              Total Cost: {{ formatCurrency(totalCost) }} of {{ formatCurrency(budget) }}
            </span>
            <div class="progress-bar-container">
              <div
                class="progress-bar-fill"
                :style="{ width: progressWidth + '%' }"
                :class="progressClass"
              ></div>
            </div>
          </div>
        </div>

        <div v-if="recommendations.length === 0" class="empty-state">
          <div class="empty-state-icon">&#8635;</div>
          <p class="empty-state-text">No items fit within budget</p>
          <p class="empty-state-hint" v-if="budget === 0">
            Increase your budget to see restocking recommendations.
          </p>
          <p class="empty-state-hint" v-else-if="demandForecasts.length === 0">
            No demand forecast data available.
          </p>
          <p class="empty-state-hint" v-else>
            All forecasted demand is at or below current demand levels.
          </p>
        </div>

        <div v-else class="table-container">
          <table class="restock-table">
            <thead>
              <tr>
                <th class="col-name">Item Name</th>
                <th class="col-sku">SKU</th>
                <th class="col-qty">Qty to Restock</th>
                <th class="col-cost">Unit Cost</th>
                <th class="col-total">Item Total</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="item in recommendations" :key="item.sku">
                <td class="col-name">
                  <span class="item-name">{{ item.name }}</span>
                </td>
                <td class="col-sku">
                  <strong>{{ item.sku }}</strong>
                </td>
                <td class="col-qty">
                  <span class="qty-badge">{{ item.quantity.toLocaleString() }}</span>
                </td>
                <td class="col-cost">{{ formatCurrency(item.unit_cost) }}</td>
                <td class="col-total">
                  <strong>{{ formatCurrency(item.quantity * item.unit_cost) }}</strong>
                </td>
              </tr>
            </tbody>
            <tfoot>
              <tr class="totals-row">
                <td colspan="2" class="totals-label">Total</td>
                <td class="col-qty">
                  <strong>{{ totalQuantity.toLocaleString() }} units</strong>
                </td>
                <td></td>
                <td class="col-total">
                  <strong>{{ formatCurrency(totalCost) }}</strong>
                </td>
              </tr>
            </tfoot>
          </table>
        </div>

        <div class="card-footer">
          <button
            class="place-order-btn"
            :disabled="recommendations.length === 0 || submitting"
            @click="placeOrder"
          >
            <span v-if="submitting">Placing Order...</span>
            <span v-else>Place Order</span>
          </button>
          <span v-if="recommendations.length === 0" class="btn-hint">
            Add budget and forecasted demand to enable ordering.
          </span>
        </div>
      </div>

    </div>
  </div>
</template>

<script>
import { ref, computed, onMounted, watch } from 'vue'
import { api } from '../api'
import { useI18n } from '../composables/useI18n'

const FALLBACK_UNIT_COST = 50

export default {
  name: 'Restocking',
  setup() {
    const { t, currentCurrency } = useI18n()

    const loading = ref(true)
    const error = ref(null)
    const submitting = ref(false)
    const successMessage = ref('')
    const successTimer = ref(null)

    const budget = ref(25000)
    const demandForecasts = ref([])
    const inventoryItems = ref([])

    // ── Currency formatting ───────────────────────────────────────────────────
    const formatCurrency = (value) => {
      const symbol = currentCurrency.value === 'JPY' ? '¥' : '$'
      if (currentCurrency.value === 'JPY') {
        return symbol + Math.round(value).toLocaleString()
      }
      return symbol + value.toLocaleString('en-US', {
        minimumFractionDigits: 0,
        maximumFractionDigits: 0
      })
    }

    // ── Recommendation algorithm ──────────────────────────────────────────────
    const recommendations = computed(() => {
      // Build a quick SKU → unit_cost lookup from inventory
      const costMap = {}
      for (const inv of inventoryItems.value) {
        costMap[inv.sku] = inv.unit_cost
      }

      // 1. Filter: only forecasts with a positive demand gap
      const gapItems = demandForecasts.value
        .filter(f => f.forecasted_demand > f.current_demand)
        .map(f => {
          const gap = f.forecasted_demand - f.current_demand
          const unit_cost = costMap[f.item_sku] !== undefined
            ? costMap[f.item_sku]
            : FALLBACK_UNIT_COST
          return {
            sku: f.item_sku,
            name: f.item_name,
            gap,
            unit_cost,
            full_cost: gap * unit_cost
          }
        })

      // 2. Sort by gap descending
      gapItems.sort((a, b) => b.gap - a.gap)

      // 3. Greedy budget fill
      let remaining = budget.value
      const result = []

      for (const item of gapItems) {
        if (remaining <= 0) break

        if (remaining >= item.full_cost) {
          result.push({
            sku: item.sku,
            name: item.name,
            quantity: item.gap,
            unit_cost: item.unit_cost
          })
          remaining -= item.full_cost
        } else {
          const partialQty = Math.floor(remaining / item.unit_cost)
          if (partialQty > 0) {
            result.push({
              sku: item.sku,
              name: item.name,
              quantity: partialQty,
              unit_cost: item.unit_cost
            })
            remaining -= partialQty * item.unit_cost
          }
          // Budget effectively exhausted
          break
        }
      }

      return result
    })

    // ── Derived totals ────────────────────────────────────────────────────────
    const totalCost = computed(() =>
      recommendations.value.reduce((sum, item) => sum + item.quantity * item.unit_cost, 0)
    )

    const totalQuantity = computed(() =>
      recommendations.value.reduce((sum, item) => sum + item.quantity, 0)
    )

    const progressWidth = computed(() => {
      if (budget.value === 0) return 0
      return Math.min((totalCost.value / budget.value) * 100, 100)
    })

    const progressClass = computed(() => {
      const pct = progressWidth.value
      if (pct >= 90) return 'progress-high'
      if (pct >= 60) return 'progress-mid'
      return 'progress-low'
    })

    // ── Data loading ──────────────────────────────────────────────────────────
    const loadData = async () => {
      try {
        loading.value = true
        error.value = null

        const [forecastsData, inventoryData] = await Promise.all([
          api.getDemandForecasts(),
          api.getInventory()
        ])

        demandForecasts.value = forecastsData
        inventoryItems.value = inventoryData
      } catch (err) {
        error.value = 'Failed to load restocking data: ' + err.message
        console.error(err)
      } finally {
        loading.value = false
      }
    }

    // ── Place order ───────────────────────────────────────────────────────────
    const placeOrder = async () => {
      if (recommendations.value.length === 0 || submitting.value) return

      try {
        submitting.value = true

        const orderPayload = {
          items: recommendations.value.map(item => ({
            sku: item.sku,
            name: item.name,
            quantity: item.quantity,
            unit_cost: item.unit_cost
          })),
          warehouse: 'all',
          category: 'all',
          total_value: totalCost.value
        }

        const result = await api.createRestockingOrder(orderPayload)

        const orderNumber = result.order_number || result.id || 'ORD-RST-0001'
        successMessage.value = `Order ${orderNumber} placed successfully. Expected delivery in 14 days.`

        // Clear any previous timer
        if (successTimer.value) clearTimeout(successTimer.value)

        // Auto-dismiss after 4 seconds and reset
        successTimer.value = setTimeout(() => {
          successMessage.value = ''
          successTimer.value = null
        }, 4000)

      } catch (err) {
        error.value = 'Failed to place order: ' + err.message
        console.error(err)
      } finally {
        submitting.value = false
      }
    }

    onMounted(loadData)

    return {
      t,
      loading,
      error,
      submitting,
      successMessage,
      budget,
      demandForecasts,
      recommendations,
      totalCost,
      totalQuantity,
      progressWidth,
      progressClass,
      formatCurrency,
      placeOrder
    }
  }
}
</script>

<style scoped>
/* ── Success Banner ─────────────────────────────────────────────────────── */
.success-banner {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  background: #d1fae5;
  border: 1px solid #6ee7b7;
  color: #065f46;
  padding: 0.875rem 1.25rem;
  border-radius: 8px;
  font-size: 0.938rem;
  font-weight: 500;
  margin-bottom: 1.25rem;
}

.success-icon {
  font-size: 1.125rem;
  font-weight: 700;
  flex-shrink: 0;
  color: #059669;
}

/* ── Budget Slider ──────────────────────────────────────────────────────── */
.budget-display {
  font-size: 1.5rem;
  font-weight: 700;
  color: #0f172a;
  letter-spacing: -0.025em;
}

.slider-section {
  padding: 0.25rem 0 0.5rem;
}

.slider-labels {
  display: flex;
  justify-content: space-between;
  font-size: 0.813rem;
  color: #64748b;
  margin-bottom: 0.5rem;
}

.budget-slider {
  width: 100%;
  height: 6px;
  -webkit-appearance: none;
  appearance: none;
  background: #e2e8f0;
  border-radius: 3px;
  outline: none;
  cursor: pointer;
  accent-color: #3b82f6;
}

.budget-slider::-webkit-slider-thumb {
  -webkit-appearance: none;
  appearance: none;
  width: 20px;
  height: 20px;
  border-radius: 50%;
  background: #3b82f6;
  cursor: pointer;
  border: 2px solid white;
  box-shadow: 0 1px 4px rgba(59, 130, 246, 0.4);
  transition: box-shadow 0.15s;
}

.budget-slider::-webkit-slider-thumb:hover {
  box-shadow: 0 2px 8px rgba(59, 130, 246, 0.5);
}

.budget-slider::-moz-range-thumb {
  width: 20px;
  height: 20px;
  border-radius: 50%;
  background: #3b82f6;
  cursor: pointer;
  border: 2px solid white;
  box-shadow: 0 1px 4px rgba(59, 130, 246, 0.4);
}

.slider-hint {
  font-size: 0.813rem;
  color: #94a3b8;
  margin-top: 0.5rem;
}

/* ── Budget Summary ─────────────────────────────────────────────────────── */
.budget-summary {
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  gap: 0.375rem;
  min-width: 220px;
}

.budget-used {
  font-size: 0.875rem;
  font-weight: 600;
  color: #475569;
}

.progress-bar-container {
  width: 220px;
  height: 6px;
  background: #e2e8f0;
  border-radius: 3px;
  overflow: hidden;
}

.progress-bar-fill {
  height: 100%;
  border-radius: 3px;
  transition: width 0.3s ease;
}

.progress-bar-fill.progress-low  { background: #10b981; }
.progress-bar-fill.progress-mid  { background: #f59e0b; }
.progress-bar-fill.progress-high { background: #ef4444; }

/* ── Item Count Badge ───────────────────────────────────────────────────── */
.item-count-badge {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  background: #dbeafe;
  color: #1e40af;
  font-size: 0.75rem;
  font-weight: 700;
  border-radius: 12px;
  padding: 0.125rem 0.625rem;
  margin-left: 0.625rem;
  vertical-align: middle;
}

/* ── Table ──────────────────────────────────────────────────────────────── */
.restock-table {
  table-layout: fixed;
  width: 100%;
}

.col-name  { width: 35%; }
.col-sku   { width: 18%; }
.col-qty   { width: 17%; }
.col-cost  { width: 15%; }
.col-total { width: 15%; }

.item-name {
  font-size: 0.875rem;
  color: #0f172a;
  font-weight: 500;
}

.qty-badge {
  display: inline-block;
  background: #f1f5f9;
  color: #0f172a;
  font-size: 0.813rem;
  font-weight: 700;
  padding: 0.188rem 0.625rem;
  border-radius: 5px;
  border: 1px solid #e2e8f0;
}

/* ── Table Footer Totals ────────────────────────────────────────────────── */
.totals-row {
  background: #f8fafc;
  border-top: 2px solid #e2e8f0;
}

.totals-row td {
  padding: 0.625rem 0.75rem;
  font-size: 0.875rem;
  color: #0f172a;
}

.totals-label {
  font-weight: 700;
  color: #475569;
  text-transform: uppercase;
  font-size: 0.75rem;
  letter-spacing: 0.05em;
}

/* ── Empty State ────────────────────────────────────────────────────────── */
.empty-state {
  text-align: center;
  padding: 3rem 2rem;
  color: #64748b;
}

.empty-state-icon {
  font-size: 2.5rem;
  margin-bottom: 0.75rem;
  color: #cbd5e1;
}

.empty-state-text {
  font-size: 1rem;
  font-weight: 600;
  color: #475569;
  margin-bottom: 0.5rem;
}

.empty-state-hint {
  font-size: 0.875rem;
  color: #94a3b8;
}

/* ── Card Footer / Place Order ──────────────────────────────────────────── */
.card-footer {
  display: flex;
  align-items: center;
  gap: 1rem;
  padding-top: 1rem;
  margin-top: 0.5rem;
  border-top: 1px solid #e2e8f0;
}

.place-order-btn {
  padding: 0.625rem 1.75rem;
  background: #2563eb;
  color: white;
  border: none;
  border-radius: 7px;
  font-size: 0.938rem;
  font-weight: 600;
  cursor: pointer;
  transition: background 0.15s, box-shadow 0.15s;
  letter-spacing: 0.01em;
}

.place-order-btn:hover:not(:disabled) {
  background: #1d4ed8;
  box-shadow: 0 2px 8px rgba(37, 99, 235, 0.35);
}

.place-order-btn:disabled {
  background: #94a3b8;
  cursor: not-allowed;
  box-shadow: none;
}

.btn-hint {
  font-size: 0.813rem;
  color: #94a3b8;
}

/* ── Responsive ─────────────────────────────────────────────────────────── */
@media (max-width: 768px) {
  .budget-summary {
    align-items: flex-start;
    min-width: unset;
    width: 100%;
  }

  .progress-bar-container {
    width: 100%;
  }

  .card-header {
    flex-direction: column;
    align-items: flex-start;
    gap: 0.75rem;
  }

  .col-name  { width: 30%; }
  .col-sku   { width: 20%; }
  .col-qty   { width: 18%; }
  .col-cost  { width: 16%; }
  .col-total { width: 16%; }
}
</style>
