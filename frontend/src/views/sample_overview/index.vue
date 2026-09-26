<template>
  <section class="page" data-module="sample-overview">
    <header class="page-head">
      <div>
        <h2>检测样品接收概览</h2>
        <p class="page-desc">集中呈现样品编号、样品名称、委托单位、样品类型，以及今日接收、待接收样品；列表与详情同页查看。</p>
      </div>
      <div class="page-actions">
        <button class="btn" type="button" @click="reload">刷新概览</button>
      </div>
    </header>

    <div class="stat-row">
      <article v-for="item in stats" :key="item.label" class="stat-card">
        <span class="stat-label">{{ item.label }}</span>
        <strong class="stat-value">{{ item.value }}</strong>
      </article>
    </div>

    <form class="filter-bar" @submit.prevent="reload">
      <label class="filter-item">
        <span>样品编号</span>
        <input v-model="filters.keyword" placeholder="按样品编号检索" />
      </label>
      <label class="filter-item">
        <span>接收状态</span>
        <select v-model="filters.status">
          <option value="">全部状态</option>
          <option v-for="status in statuses" :key="status" :value="status">{{ status }}</option>
        </select>
      </label>
      <button class="btn" type="submit">查询</button>
      <button class="btn ghost" type="button" @click="resetFilters">重置条件</button>
    </form>

    <table class="data-table">
      <thead>
        <tr>
          <th v-for="column in columns" :key="column">{{ column }}</th>
          <th>操作</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="row in rows" :key="String(row.id)">
          <td v-for="column in columns" :key="column">{{ row[column] ?? '—' }}</td>
          <td class="row-actions">
            <button class="link" type="button" @click="openDetail(row)">查看详情</button>
          </td>
        </tr>
        <tr v-if="!rows.length && !errorMessage">
          <td :colspan="columns.length + 1" class="empty-state">
            当前条件下暂无检测样品记录，可调整样品编号或接收状态后重新查询
          </td>
        </tr>
        <tr v-if="!rows.length && errorMessage">
          <td :colspan="columns.length + 1" class="empty-state">读取未完成，当前筛选条件已保留</td>
        </tr>
      </tbody>
    </table>

    <footer class="page-foot">
      <span>当前条件下共 {{ total }} 条检测样品记录</span>
      <span v-if="errorMessage" class="error-text">{{ errorMessage }}</span>
    </footer>

    <section v-if="detail || detailError" class="detail-panel">
      <header class="detail-head">
        <h3>检测样品详情</h3>
        <button class="btn ghost" type="button" @click="closeDetail">关闭</button>
      </header>
      <p v-if="detailError" class="error-text">{{ detailError }}</p>
      <table v-if="detail" class="data-table detail-table">
        <tbody>
          <tr v-for="field in detailFields" :key="field">
            <th>{{ field }}</th>
            <td>{{ field === '接收状态' ? detail.status ?? '—' : detail[field] ?? '—' }}</td>
          </tr>
        </tbody>
      </table>
    </section>
  </section>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'

import { request } from '@/api/client'

type Row = Record<string, string | number | null>

const ENDPOINT = '/api/sample'
const columns = ["样品编号", "样品名称", "委托单位", "样品类型", "接收日期", "接收状态"]
const detailFields = ["样品编号", "样品名称", "委托单位", "样品类型", "接收日期", "保存条件", "送样人员", "接收状态"]
const statuses = ["待接收", "已接收", "已退回", "已废弃"]

const stats = ref<{ label: string; value: number }[]>([])
const rows = ref<Row[]>([])
const total = ref(0)
const errorMessage = ref('')
const filters = ref({ keyword: '', status: '' })
const detail = ref<Row | null>(null)
const detailError = ref('')

function resetFilters() {
  filters.value = { keyword: '', status: '' }
  void reload()
}

function closeDetail() {
  detail.value = null
  detailError.value = ''
}

async function readError(response: Response, fallback: string): Promise<string> {
  try {
    const body = await response.json()
    if (body && typeof body.detail === 'string') {
      return body.detail
    }
  } catch {
    // 响应体不是 JSON 时走兜底说明
  }
  return fallback
}

async function openDetail(row: Row) {
  detail.value = null
  detailError.value = ''
  try {
    const response = await request(`${ENDPOINT}/${row.id}`)
    if (!response.ok) {
      throw new Error(await readError(response, `检测样品 ${row.id} 详情读取失败`))
    }
    detail.value = await response.json()
  } catch (error) {
    detailError.value = error instanceof Error ? error.message : '检测样品详情读取失败'
  }
}

async function reload() {
  errorMessage.value = ''
  const query = new URLSearchParams()
  if (filters.value.keyword.trim()) {
    query.set('keyword', filters.value.keyword.trim())
  }
  if (filters.value.status) {
    query.set('status', filters.value.status)
  }
  try {
    const response = await request(`${ENDPOINT}/overview?${query.toString()}`)
    if (!response.ok) {
      throw new Error(await readError(response, `概览读取失败（${response.status}），当前筛选条件已保留`))
    }
    const payload = await response.json()
    // 统计卡片、列表、总数来自同一次响应，数量口径始终一致
    stats.value = payload.stats ?? []
    rows.value = payload.items ?? []
    total.value = payload.total ?? rows.value.length
    if (detail.value) {
      // 列表刷新后同步刷新已打开的详情，避免展示过期记录
      await openDetail(detail.value)
    }
  } catch (error) {
    rows.value = []
    total.value = 0
    stats.value = []
    errorMessage.value = error instanceof Error ? error.message : '样品接收概览读取失败，当前筛选条件已保留'
  }
}

onMounted(reload)
</script>

<style scoped>
.detail-panel {
  margin-top: 16px;
  background: #fff;
  border: 1px solid var(--border);
  border-radius: 8px;
  padding: 12px 16px;
}
.detail-head {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
.detail-head h3 {
  margin: 0;
  font-size: 15px;
}
.detail-table {
  margin-top: 10px;
}
.detail-table th {
  width: 120px;
  background: #f8fafc;
}
</style>
