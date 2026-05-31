import { useState, useEffect, useCallback } from 'react'
import {
  Row, Col, Card, Typography, Button, Space, message, Table, Tag, Select,
  Drawer, Form, InputNumber, Progress, Statistic, Popconfirm, Divider,
} from 'antd'
import {
  ThunderboltOutlined, RobotOutlined, RocketOutlined, EditOutlined,
  HistoryOutlined, ReloadOutlined, CheckCircleOutlined, CloseCircleOutlined,
} from '@ant-design/icons'
import { getTaggingStats, getTaggingResults, triggerTagging, getTaggingTaskStatus,
         manualUpdateTagging, getTaggingHistory } from '../services/taggingService'
import { getCategories } from '../services/standardService'
import { useAuth } from '../hooks/useAuth'

const { Title, Text } = Typography
const { Option } = Select

const TIER_COLORS = { L1: 'green', L2: 'blue', L3: 'orange', L4: 'red' }
const METHOD_LABELS = { rule_engine: '规则引擎', ai: 'AI辅助', manual: '人工', hybrid: '混合' }

export default function TaggingPage() {
  const { hasRole } = useAuth()
  const canEdit = hasRole('data_admin', 'admin')

  const [data, setData] = useState({ items: [], total: 0 })
  const [loading, setLoading] = useState(false)
  const [stats, setStats] = useState(null)
  const [filters, setFilters] = useState({ page: 1, page_size: 20 })
  const [taskId, setTaskId] = useState(null)
  const [taskRunning, setTaskRunning] = useState(false)
  const [drawerOpen, setDrawerOpen] = useState(false)
  const [editingField, setEditingField] = useState(null)
  const [history, setHistory] = useState([])
  const [categories, setCategories] = useState([])
  const [submitting, setSubmitting] = useState(false)
  const [selectedRows, setSelectedRows] = useState([])

  const load = useCallback(async () => {
    setLoading(true)
    try {
      const [res, s] = await Promise.all([
        getTaggingResults(filters),
        getTaggingStats(),
      ])
      setData(res)
      setStats(s)
    } catch { message.error('加载数据失败') }
    finally { setLoading(false) }
  }, [filters])

  useEffect(() => { load() }, [load])

  useEffect(() => {
    getCategories().then(setCategories).catch(() => {})
  }, [])

  // Pipeline trigger
  const runPipeline = async (mode) => {
    setTaskRunning(true)
    try {
      const { task_id } = await triggerTagging(mode)
      setTaskId(task_id)
      pollTask(task_id)
    } catch { message.error('启动失败'); setTaskRunning(false) }
  }

  const pollTask = (tid) => {
    const interval = setInterval(async () => {
      try {
        const status = await getTaggingTaskStatus(tid)
        if (status.status === 'completed' || status.status === 'failed') {
          clearInterval(interval)
          setTaskRunning(false)
          if (status.status === 'completed') {
            message.success(`打标完成: ${status.processed} 个字段, ${status.classified} 已分类, ${status.tiered} 已分级`)
          } else {
            message.error('打标失败: ' + JSON.stringify(status.errors))
          }
          load()
        }
      } catch { clearInterval(interval); setTaskRunning(false) }
    }, 1500)
  }

  // Manual edit
  const handleEdit = (record) => {
    setEditingField(record)
    getTaggingHistory(record.id).then(setHistory).catch(() => setHistory([]))
    setDrawerOpen(true)
  }

  const handleSubmit = async () => {
    setSubmitting(true)
    try {
      await manualUpdateTagging(editingField.id, {
        category_id: editingField.classification_id,
        tier_level: editingField.sensitivity_level,
        confidence: editingField.tagging_confidence || 1.0,
        comment: '人工修正',
      })
      message.success('已更新')
      setDrawerOpen(false)
      load()
    } catch (err) { message.error(err.response?.data?.detail || '操作失败') }
    finally { setSubmitting(false) }
  }

  const columns = [
    { title: '字段编码', dataIndex: 'field_code', key: 'field_code', width: 110 },
    { title: '字段名称', dataIndex: 'name', key: 'name', width: 120 },
    { title: '表名', dataIndex: 'table_name', key: 'table_name', width: 140, ellipsis: true },
    { title: '业务域', dataIndex: 'business_domain', key: 'business_domain', width: 100 },
    {
      title: '分类', dataIndex: 'classification_name', key: 'classification_name', width: 130,
      render: (v) => v ? <Tag color="blue">{v}</Tag> : <Text type="secondary">未分类</Text>,
    },
    {
      title: '分级', dataIndex: 'sensitivity_level', key: 'sensitivity_level', width: 80,
      render: (v) => <Tag color={TIER_COLORS[v]}>{v}</Tag>,
    },
    {
      title: '方法', dataIndex: 'tagging_method', key: 'tagging_method', width: 90,
      render: (v) => v ? <Tag>{METHOD_LABELS[v] || v}</Tag> : <Text type="secondary">-</Text>,
    },
    {
      title: '置信度', dataIndex: 'tagging_confidence', key: 'tagging_confidence', width: 90,
      render: (v) => v != null ? <Progress percent={Math.round(v * 100)} size="small" style={{ width: 60 }} /> : '-',
    },
    ...(canEdit ? [{
      title: '操作', key: 'actions', width: 80,
      render: (_, record) => (
        <Button size="small" icon={<EditOutlined />} onClick={() => handleEdit(record)}>修正</Button>
      ),
    }] : []),
  ]

  return (
    <div>
      <Title level={3}>数据打标</Title>

      {/* Stats cards */}
      {stats && (
        <Row gutter={16} style={{ marginBottom: 16 }}>
          <Col xs={12} sm={6}><Card><Statistic title="总字段" value={stats.total_fields} /></Card></Col>
          <Col xs={12} sm={6}><Card><Statistic title="已分类" value={stats.classified_count} suffix={`/ ${stats.total_fields}`} /></Card></Col>
          <Col xs={12} sm={6}><Card><Statistic title="覆盖率" value={stats.coverage_pct} suffix="%" /></Card></Col>
          <Col xs={12} sm={6}><Card><Statistic title="未分类" value={stats.unclassified_count} valueStyle={{ color: stats.unclassified_count > 0 ? '#cf1322' : undefined }} /></Card></Col>
        </Row>
      )}

      {/* Action bar */}
      <Card style={{ marginBottom: 16 }}>
        <Space wrap>
          <Button type="primary" icon={<ThunderboltOutlined />} loading={taskRunning}
            onClick={() => runPipeline('rules_only')} disabled={taskRunning}>
            运行规则引擎
          </Button>
          <Button icon={<RobotOutlined />} loading={taskRunning}
            onClick={() => runPipeline('ai_only')} disabled={taskRunning}>
            AI辅助分析
          </Button>
          <Button icon={<RocketOutlined />} loading={taskRunning}
            onClick={() => runPipeline('full')} disabled={taskRunning}>
            全流水线
          </Button>
          <Divider type="vertical" />
          <Select allowClear placeholder="分级筛选" style={{ width: 100 }}
            value={filters.tier_level} onChange={(v) => setFilters(f => ({ ...f, tier_level: v, page: 1 }))}>
            {['L1','L2','L3','L4'].map(t => <Option key={t} value={t}>{t}</Option>)}
          </Select>
          <Select allowClear placeholder="方法筛选" style={{ width: 120 }}
            value={filters.method} onChange={(v) => setFilters(f => ({ ...f, method: v, page: 1 }))}>
            {Object.entries(METHOD_LABELS).map(([k, v]) => <Option key={k} value={k}>{v}</Option>)}
          </Select>
          <Select allowClear placeholder="标状态" style={{ width: 120 }}
            value={filters.is_tagged} onChange={(v) => setFilters(f => ({ ...f, is_tagged: v, page: 1 }))}>
            <Option value={true}>已打标</Option>
            <Option value={false}>未打标</Option>
          </Select>
          <Button icon={<ReloadOutlined />} onClick={load}>刷新</Button>
        </Space>
      </Card>

      {/* Results table */}
      <Table
        columns={columns}
        dataSource={data.items}
        rowKey="id"
        loading={loading}
        rowSelection={canEdit ? { selectedRowKeys: selectedRows, onChange: setSelectedRows } : undefined}
        pagination={{
          current: filters.page, pageSize: filters.page_size, total: data.total,
          onChange: (p, ps) => setFilters(f => ({ ...f, page: p, page_size: ps })),
          showTotal: (t) => `共 ${t} 条`,
        }}
      />

      {/* Edit drawer */}
      <Drawer
        title={`修正打标: ${editingField?.field_code} ${editingField?.name}`}
        open={drawerOpen}
        onClose={() => setDrawerOpen(false)}
        width={480}
        extra={
          <Space>
            <Button onClick={() => setDrawerOpen(false)}>取消</Button>
            <Button type="primary" onClick={handleSubmit} loading={submitting}>保存</Button>
          </Space>
        }
      >
        {editingField && (
          <>
            <div style={{ marginBottom: 16 }}>
              <Text strong>分类:</Text>
              <Select
                style={{ width: '100%', marginTop: 4 }}
                value={editingField.classification_id}
                onChange={(v) => setEditingField(f => ({ ...f, classification_id: v }))}
              >
                <Option value={null}>未分类</Option>
                {categories.map(c => <Option key={c.id} value={c.id}>{'  '.repeat(c.level)}{c.name}</Option>)}
              </Select>
            </div>
            <div style={{ marginBottom: 16 }}>
              <Text strong>分级:</Text>
              <Select
                style={{ width: '100%', marginTop: 4 }}
                value={editingField.sensitivity_level}
                onChange={(v) => setEditingField(f => ({ ...f, sensitivity_level: v }))}
              >
                {['L1','L2','L3','L4'].map(t => <Option key={t} value={t}>{t}</Option>)}
              </Select>
            </div>
            <div style={{ marginBottom: 16 }}>
              <Text strong>置信度:</Text>
              <InputNumber min={0} max={1} step={0.1} style={{ width: '100%', marginTop: 4 }}
                value={editingField.tagging_confidence}
                onChange={(v) => setEditingField(f => ({ ...f, tagging_confidence: v }))} />
            </div>

            <Divider />
            <Title level={5}><HistoryOutlined /> 打标历史</Title>
            {history.length === 0 ? (
              <Text type="secondary">暂无记录</Text>
            ) : (
              history.map(h => (
                <Card key={h.id} size="small" style={{ marginBottom: 8 }}>
                  <p><Tag>{h.action}</Tag> <Text type="secondary">{h.created_at}</Text></p>
                  {h.old_tier_level && <p>分级: <Tag color={TIER_COLORS[h.old_tier_level]}>{h.old_tier_level}</Tag> → <Tag color={TIER_COLORS[h.new_tier_level]}>{h.new_tier_level}</Tag></p>}
                  <p>方法: {METHOD_LABELS[h.tagging_method] || h.tagging_method} | 置信度: {h.new_confidence}</p>
                  {h.comment && <p><Text type="secondary">{h.comment}</Text></p>}
                </Card>
              ))
            )}
          </>
        )}
      </Drawer>
    </div>
  )
}
