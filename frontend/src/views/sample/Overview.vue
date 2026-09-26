<template>
  <section class="page sample-overview" data-module="sample-overview">
    <header class="page-head">
      <div>
        <h2>检测样品接收概览</h2>
        <p class="page-desc">集中查看样品编号、样品名称、委托单位、样品类型，以及今日接收和待接收样品；左侧列表与右侧详情共用当前筛选条件。</p>
      </div>
      <div class="page-actions">
        <RouterLink class="btn" to="/sample">进入样品接收管理</RouterLink>
        <button class="btn ghost" type="button" @click="reloadAll">刷新概览</button>
      </div>
    </header>

    <div class="stat-row">
      <article v-for="card in displayCards" :key="card.label" class="stat-card" :class="{ stale: overviewError }">
        <span class="stat-label">{{ card.label }}</span>
        <strong class="stat-value">{{ card.value }}</strong>
        <small v-if="overviewError" class="stat-note">读取失败，显示上次有效数量</small>
        <small v-else-if="overviewData" class="stat-note">统计日期：{{ overviewData.date }}</small>
      </article>
    </div>

    <form class="filter-bar" @submit.prevent="applyFilters">
      <label class="filter-item">
        <span>样品编号</span>
        <input v-model="filters.keyword" placeholder="按样品编号检索" />
      </label>
      <label class="filter-item">
        <span>样品名称</span>
        <input v-model="filters.sampleName" placeholder="按样品名称检索" />
      </label>
      <label class="filter-item">
        <span>委托单位</span>
        <input v-model="filters.client" placeholder="按委托单位检索" />
      </label>
      <label class="filter-item">
        <span>样品类型</span>
        <input v-model="filters.sampleType" placeholder="按样品类型检索" />
      </label>
      <label class="filter-item">
        <span>接收状态</span>
        <select v-model="filters.status">
          <option value="">全部状态</option>
          <option v-for="status in statusOptions" :key="status" :value="status">{{ status }}</option>
        </select>
      </label>
      <button class="btn primary" type="submit">查询</button>
      <button class="btn ghost" type="button" @click="resetFilters">重置条件</button>
    </form>

    <div v-if="overviewError" class="inline-alert error" role="alert">
      <strong>概览读取失败，当前条件已保留。</strong>
      <span>{{ overviewError }}</span>
      <small>{{ conditionSummary || '未设置筛选条件' }}</small>
    </div>

    <div class="overview-layout">
      <section class="list-panel">
        <div class="panel-head">
          <h3>样品列表</h3>
          <span v-if="listLoading" class="panel-state">读取中…</span>
        </div>
        <table class="data-table">
          <thead>
            <tr>
              <th v-for="column in columns" :key="column">{{ column }}</th>
              <th>接收日期</th>
              <th>接收状态</th>
            </tr>
          </thead>
          <tbody>
            <tr
              v-for="row in items"
              :key="String(row.id)"
              :class="{ selected: Number(selectedId) === Number(row.id) }"
              tabindex="0"
              @click="openDetail(Number(row.id))"
              @keydown.enter="openDetail(Number(row.id))"
            >
              <td v-for="column in columns" :key="column">{{ row[column] || '—' }}</td>
              <td>{{ row.接收日期 || '—' }}</td>
              <td><span class="status-pill" :data-status="row.接收状态">{{ row.接收状态 || '—' }}</span></td>
            </tr>
            <tr v-if="!listLoading && !items.length">
              <td :colspan="columns.length + 2" class="empty-state">
                {{ emptyMessage }}
              </td>
            </tr>
          </tbody>
        </table>
        <footer class="panel-foot">
          <span>当前条件共 <strong>{{ overviewData?.total ?? '—' }}</strong> 条记录</span>
          <span v-if="overviewData">今日接收 {{ cardValue('今日接收') }} · 待接收 {{ cardValue('待接收样品') }}</span>
        </footer>
      </section>

      <aside class="detail-panel" aria-live="polite">
        <div class="panel-head">
          <h3>样品详情</h3>
          <button v-if="selectedId" class="link" type="button" @click="clearDetail">返回列表</button>
        </div>

        <div v-if="!selectedId" class="detail-placeholder">
          <strong>请选择左侧样品</strong>
          <p>也可以使用 /sample/overview?id=样品ID 的方式直接打开指定样品详情。</p>
        </div>

        <div v-else-if="detailLoading" class="detail-placeholder">
          <strong>正在读取样品 {{ selectedId }}…</strong>
          <p>当前筛选条件不会被清空。</p>
        </div>

        <template v-else-if="detail">
          <dl class="detail-list">
            <template v-for="field in detailFields" :key="field.key">
              <dt>{{ field.label }}</dt>
              <dd>{{ field.value || '—' }}</dd>
            </template>
            <dt>当前状态</dt>
            <dd><span class="status-pill" :data-status="detailStatus">{{ detailStatus || '—' }}</span></dd>
          </dl>
        </template>

        <div v-else class="detail-placeholder error-state">
          <strong v-if="detailNotFound">未找到样品 {{ selectedId }}</strong>
          <strong v-else-if="detailError">样品详情读取失败，当前选择已保留。</strong>
          <p>{{ detailNotFound ? '该样品可能已被归档，或不在当前条件中；当前样品编号和筛选条件已保留。' : detailError }}</p>
          <dl v-if="selectedListRow" class="fallback-summary">
            <dt>样品编号</dt><dd>{{ selectedListRow.样品编号 || '—' }}</dd>
            <dt>样品名称</dt><dd>{{ selectedListRow.样品名称 || '—' }}</dd>
            <dt>委托单位</dt><dd>{{ selectedListRow.委托单位 || '—' }}</dd>
            <dt>样品类型</dt><dd>{{ selectedListRow.样品类型 || '—' }}</dd>
          </dl>
          <button class="btn" type="button" @click="loadDetail">重试读取详情</button>
        </div>
      </aside>
    </div>
  </section>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'

import { request } from '@/api/client'

type SampleRow = {
  id: number | null
  样品编号: string | null
  样品名称: string | null
  委托单位: string | null
  样品类型: string | null
  接收日期?: string | null
  接收状态: string | null
}

type SampleDetail = Record<string, string | number | boolean | null>

type OverviewPayload = {
  date: string
  total: number
  cards: { label: string; value: number }[]
  items: SampleRow[]
}

type Filters = {
  keyword: string
  sampleName: string
  client: string
  sampleType: string
  status: string
}

const route = useRoute()
const router = useRouter()

const columns = ['样品编号', '样品名称', '委托单位', '样品类型'] as const
const statusOptions = ['待接收', '已接收', '已退回', '已废弃']
const emptyFilters = (): Filters => ({ keyword: '', sampleName: '', client: '', sampleType: '', status: '' })

const filters = ref<Filters>(emptyFilters())
const selectedId = ref<number | null>(null)
const overviewData = ref<OverviewPayload | null>(null)
const detail = ref<SampleDetail | null>(null)
const listLoading = ref(false)
const detailLoading = ref(false)
const overviewError = ref('')
const detailError = ref('')
const detailNotFound = ref(false)

let overviewRequestId = 0
let detailRequestId = 0

const items = computed(() => overviewData.value?.items ?? [])
const selectedListRow = computed(() => items.value.find((row) => Number(row.id) === Number(selectedId.value)))

const displayCards = computed(() => {
  if (overviewData.value) return overviewData.value.cards
  return [
    { label: '今日接收', value: '—' },
    { label: '待接收样品', value: '—' },
  ]
})

const detailStatus = computed(() => String(detail.value?.status ?? detail.value?.接收状态 ?? ''))

const detailFields = computed(() => [
  { label: '样品编号', key: '样品编号', value: detail.value?.['样品编号'] },
  { label: '样品名称', key: '样品名称', value: detail.value?.['样品名称'] },
  { label: '委托单位', key: '委托单位', value: detail.value?.['委托单位'] },
  { label: '样品类型', key: '样品类型', value: detail.value?.['样品类型'] },
  { label: '接收日期', key: '接收日期', value: detail.value?.['接收日期'] },
  { label: '保存条件', key: '保存条件', value: detail.value?.['保存条件'] },
  { label: '送样人员', key: '送样人员', value: detail.value?.['送样人员'] },
])

const activeFilters = computed(() => {
  const query: Record<string, string> = {}
  if (filters.value.keyword.trim()) query.keyword = filters.value.keyword.trim()
  if (filters.value.sampleName.trim()) query.sampleName = filters.value.sampleName.trim()
  if (filters.value.client.trim()) query.client = filters.value.client.trim()
  if (filters.value.sampleType.trim()) query.sampleType = filters.value.sampleType.trim()
  if (filters.value.status) query.status = filters.value.status
  if (selectedId.value !== null) query.id = String(selectedId.value)
  return query
})

const conditionSummary = computed(() => {
  const labels: Record<string, string> = {
    keyword: `样品编号：${filters.value.keyword.trim()}`,
    sampleName: `样品名称：${filters.value.sampleName.trim()}`,
    client: `委托单位：${filters.value.client.trim()}`,
    sampleType: `样品类型：${filters.value.sampleType.trim()}`,
    status: `接收状态：${filters.value.status}`,
  }
  return Object.keys(activeFilters.value)
    .filter((key) => key !== 'id')
    .map((key) => labels[key])
    .join('；')
})

const emptyMessage = computed(() => {
  if (overviewError.value) return '概览读取失败，列表仍保留上次成功读取的记录和筛选条件'
  return conditionSummary.value
    ? `当前条件下暂无样品记录，筛选条件已保留：${conditionSummary.value}`
    : '暂无样品接收记录'
})

function cardValue(label: string): number | string {
  return overviewData.value?.cards.find((card) => card.label === label)?.value ?? '—'
}

function readRouteState() {
  filters.value = {
    keyword: String(route.query.keyword ?? ''),
    sampleName: String(route.query.sampleName ?? ''),
    client: String(route.query.client ?? ''),
    sampleType: String(route.query.sampleType ?? ''),
    status: String(route.query.status ?? ''),
  }
  const id = Number(route.query.id)
  selectedId.value = route.query.id && Number.isFinite(id) ? id : null
}

async function syncQueryAndLoad(load: () => Promise<void>) {
  const nextQuery = activeFilters.value
  const currentQuery = JSON.stringify(route.query)
  const targetQuery = JSON.stringify(nextQuery)
  if (currentQuery !== targetQuery) {
    await router.replace({ path: '/sample/overview', query: nextQuery })
    return
  }
  await load()
}

function applyFilters() {
  void syncQueryAndLoad(loadOverview)
}

async function resetFilters() {
  filters.value = emptyFilters()
  await syncQueryAndLoad(loadOverview)
}

async function openDetail(id: number) {
  selectedId.value = id
  await syncQueryAndLoad(loadDetail)
}

async function clearDetail() {
  selectedId.value = null
  detail.value = null
  detailError.value = ''
  await syncQueryAndLoad(loadDetail)
}

async function reloadAll() {
  await Promise.all([loadOverview(), loadDetail()])
}

function overviewQuery() {
  const params = new URLSearchParams()
  if (filters.value.keyword.trim()) params.set('keyword', filters.value.keyword.trim())
  if (filters.value.sampleName.trim()) params.set('sampleName', filters.value.sampleName.trim())
  if (filters.value.client.trim()) params.set('client', filters.value.client.trim())
  if (filters.value.sampleType.trim()) params.set('sampleType', filters.value.sampleType.trim())
  if (filters.value.status) params.set('status', filters.value.status)
  const query = params.toString()
  return query ? `/api/sample/overview?${query}` : '/api/sample/overview'
}

async function loadOverview() {
  const requestId = ++overviewRequestId
  listLoading.value = true
  overviewError.value = ''
  try {
    const response = await request(overviewQuery())
    if (!response.ok) {
      throw new Error(`接口返回 ${response.status}，样品数量和列表未更新；请稍后重试。`)
    }
    const payload = (await response.json()) as OverviewPayload
    if (requestId !== overviewRequestId) return
    overviewData.value = payload
  } catch (error) {
    if (requestId !== overviewRequestId) return
    overviewError.value = error instanceof Error ? error.message : '检测样品概览读取失败'
  } finally {
    if (requestId === overviewRequestId) listLoading.value = false
  }
}

async function loadDetail() {
  if (selectedId.value === null) {
    detail.value = null
    detailError.value = ''
    detailNotFound.value = false
    detailLoading.value = false
    return
  }

  const requestId = ++detailRequestId
  const targetId = selectedId.value
  let notFound = false
  if (detail.value === null || Number(detail.value.id) !== targetId) {
    detail.value = null
  }
  detailLoading.value = true
  detailError.value = ''
  detailNotFound.value = false
  try {
    const response = await request(`/api/sample/${targetId}`)
    if (response.status === 404) {
      notFound = true
      throw new Error('该样品不存在、已归档，或当前账号暂无查看权限。')
    }
    if (!response.ok) {
      throw new Error(`接口返回 ${response.status}，无法读取该样品完整信息。`)
    }
    const payload = (await response.json()) as SampleDetail
    if (requestId !== detailRequestId) return
    detail.value = payload
  } catch (error) {
    if (requestId !== detailRequestId) return
    detail.value = null
    detailNotFound.value = notFound
    detailError.value = error instanceof Error ? error.message : '样品详情读取失败'
  } finally {
    if (requestId === detailRequestId) detailLoading.value = false
  }
}

watch(
  () => route.query,
  async () => {
    readRouteState()
    await Promise.all([loadOverview(), loadDetail()])
  },
  { immediate: true },
)
</script>

<style scoped>
.page-actions {
  display: flex;
  align-items: center;
  gap: 8px;
}

.page-actions .btn {
  display: inline-flex;
  align-items: center;
  text-decoration: none;
  color: #1f2937;
}

.stat-card.stale {
  border-color: #fecdca;
  background: #fff8f7;
}

.stat-note {
  display: block;
  margin-top: 6px;
  color: #64748b;
  font-size: 12px;
}

.stale .stat-note {
  color: #b42318;
}

.filter-item select {
  min-width: 128px;
  border: 1px solid #d8dee6;
  border-radius: 6px;
  padding: 6px 8px;
  background: #fff;
}

.inline-alert {
  display: flex;
  align-items: center;
  gap: 8px;
  margin: 0 0 12px;
  padding: 10px 12px;
  border: 1px solid #fecdca;
  border-radius: 8px;
  background: #fff8f7;
  color: #b42318;
  font-size: 13px;
}

.inline-alert small {
  margin-left: auto;
  color: #7a271a;
}

.overview-layout {
  display: grid;
  grid-template-columns: minmax(0, 2fr) minmax(300px, 1fr);
  gap: 12px;
}

.list-panel,
.detail-panel {
  min-width: 0;
  background: #fff;
  border: 1px solid #d8dee6;
  border-radius: 8px;
  overflow: hidden;
}

.panel-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 10px 12px;
  border-bottom: 1px solid #d8dee6;
}

.panel-head h3 {
  margin: 0;
  font-size: 15px;
}

.panel-state {
  color: #64748b;
  font-size: 12px;
}

.list-panel .data-table {
  border: 0;
}

.data-table tbody tr {
  cursor: pointer;
}

.data-table tbody tr:focus-visible,
.data-table tbody tr.selected {
  outline: 2px solid #1f6feb;
  outline-offset: -2px;
  background: #eff6ff;
}

.status-pill {
  display: inline-block;
  border-radius: 999px;
  padding: 2px 8px;
  font-size: 12px;
  background: #f1f5f9;
}

.status-pill[data-status='待接收'] {
  background: #fef3c7;
  color: #92400e;
}

.status-pill[data-status='已接收'] {
  background: #dcfce7;
  color: #166534;
}

.status-pill[data-status='已退回'],
.status-pill[data-status='已废弃'] {
  background: #fee2e2;
  color: #991b1b;
}

.panel-foot {
  display: flex;
  justify-content: space-between;
  gap: 8px;
  padding: 9px 12px;
  color: #64748b;
  font-size: 12px;
  border-top: 1px solid #d8dee6;
}

.detail-placeholder {
  padding: 20px 16px;
  color: #64748b;
  line-height: 1.7;
}

.detail-placeholder strong {
  color: #1f2937;
}

.detail-placeholder p {
  margin: 6px 0 12px;
  font-size: 13px;
}

.detail-list,
.fallback-summary {
  display: grid;
  grid-template-columns: 92px minmax(0, 1fr);
  gap: 0;
  margin: 0;
}

.detail-list dt,
.detail-list dd,
.fallback-summary dt,
.fallback-summary dd {
  margin: 0;
  padding: 10px 12px;
  border-bottom: 1px solid #edf1f5;
  font-size: 13px;
  word-break: break-all;
}

.detail-list dt,
.fallback-summary dt {
  color: #64748b;
  background: #f8fafc;
}

.error-state {
  color: #b42318;
}

.fallback-summary {
  margin: 12px 0;
  border: 1px solid #fecdca;
}

.fallback-summary dt,
.fallback-summary dd {
  color: #7a271a;
}

@media (max-width: 980px) {
  .overview-layout {
    grid-template-columns: 1fr;
  }

  .inline-alert {
    align-items: flex-start;
    flex-direction: column;
  }

  .inline-alert small {
    margin-left: 0;
  }
}
</style>
