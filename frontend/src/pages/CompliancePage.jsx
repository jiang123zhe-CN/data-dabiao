import { useState, useEffect, useCallback } from 'react'
import { Row, Col, Card, Typography, Statistic, Table, Tag, Button, Space, message, Tabs } from 'antd'
import { DownloadOutlined, WarningOutlined, CheckCircleOutlined, AuditOutlined } from '@ant-design/icons'
import { getComplianceSummary, getComplianceCategoryTier, getComplianceAuditTrail,
         getComplianceTaggingHistory, getComplianceGaps, exportComplianceReport } from '../services/complianceService'

const { Title, Text } = Typography
const TIER_COLORS = { L1: 'green', L2: 'blue', L3: 'orange', L4: 'red' }

export default function CompliancePage() {
  const [summary, setSummary] = useState(null)
  const [categoryTier, setCategoryTier] = useState([])
  const [auditTrail, setAuditTrail] = useState({ items: [], total: 0 })
  const [taggingHistory, setTaggingHistory] = useState({ items: [], total: 0 })
  const [gaps, setGaps] = useState(null)
  const [loading, setLoading] = useState(false)

  const load = useCallback(async () => {
    setLoading(true)
    try {
      const [s, ct, at, th, g] = await Promise.all([
        getComplianceSummary(), getComplianceCategoryTier(),
        getComplianceAuditTrail({ page: 1, page_size: 50 }),
        getComplianceTaggingHistory({ page: 1, page_size: 50 }),
        getComplianceGaps(),
      ])
      setSummary(s); setCategoryTier(ct); setAuditTrail(at);
      setTaggingHistory(th); setGaps(g)
    } catch { message.error('加载合规数据失败') }
    finally { setLoading(false) }
  }, [])

  useEffect(() => { load() }, [load])

  const auditColumns = [
    { title: '时间', dataIndex: 'created_at', key: 'created_at', width: 160, render: v => v?.substring(0, 19) },
    { title: '用户', dataIndex: 'username', key: 'username', width: 100 },
    { title: '操作', dataIndex: 'action', key: 'action', width: 80, render: v => <Tag>{v}</Tag> },
    { title: '模块', dataIndex: 'module', key: 'module', width: 100 },
    { title: '目标', dataIndex: 'target_type', key: 'target_type', width: 100 },
    { title: '详情', dataIndex: 'detail', key: 'detail', ellipsis: true },
  ]

  const historyColumns = [
    { title: '时间', dataIndex: 'created_at', key: 'created_at', width: 160, render: v => v?.substring(0, 19) },
    { title: '字段', dataIndex: 'field_name', key: 'field_name', width: 120 },
    { title: '操作', dataIndex: 'action', key: 'action', width: 100, render: v => <Tag>{v}</Tag> },
    { title: '原分级', dataIndex: 'old_tier', width: 80, render: v => v ? <Tag color={TIER_COLORS[v]}>{v}</Tag> : '-' },
    { title: '新分级', dataIndex: 'new_tier', width: 80, render: v => v ? <Tag color={TIER_COLORS[v]}>{v}</Tag> : '-' },
    { title: '方法', dataIndex: 'method', key: 'method', width: 80 },
    { title: '备注', dataIndex: 'comment', key: 'comment', ellipsis: true },
  ]

  const gapColumns = [
    { title: '字段编码', dataIndex: 'field_code', width: 110 },
    { title: '字段名', dataIndex: 'name', width: 120 },
    { title: '表名', dataIndex: 'table_name', width: 150 },
    { title: '问题', dataIndex: 'issue', width: 100, render: v => <Tag color="error">{v}</Tag> },
  ]

  // Build heatmap data
  const renderHeatmap = () => {
    const categories = [...new Set(categoryTier.map(d => d.category))]
    const tiers = ['L1', 'L2', 'L3', 'L4', '未分级']
    const matrix = {}
    categoryTier.forEach(d => { matrix[`${d.category}|${d.tier}`] = d.count })

    return (
      <div style={{ overflow: 'auto' }}>
        <table style={{ borderCollapse: 'collapse', width: '100%' }}>
          <thead>
            <tr>
              <th style={{ padding: 8, border: '1px solid #f0f0f0', background: '#fafafa' }}>分类 \\ 分级</th>
              {tiers.map(t => <th key={t} style={{ padding: 8, border: '1px solid #f0f0f0', background: '#fafafa' }}>{t}</th>)}
            </tr>
          </thead>
          <tbody>
            {categories.map(cat => (
              <tr key={cat}>
                <td style={{ padding: 8, border: '1px solid #f0f0f0', fontWeight: 500 }}>{cat}</td>
                {tiers.map(t => {
                  const v = matrix[`${cat}|${t}`] || 0
                  const intensity = v > 0 ? Math.min(v * 40 + 200, 255) : 255
                  return (
                    <td key={t} style={{
                      padding: 8, border: '1px solid #f0f0f0', textAlign: 'center',
                      background: v > 0 ? `rgba(22,119,255,${v * 0.2})` : '#fff',
                      color: v > 0 ? '#1677ff' : '#ccc',
                    }}>{v || '-'}</td>
                  )
                })}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    )
  }

  const tabItems = [
    {
      key: 'overview',
      label: <span><CheckCircleOutlined /> 合规总览</span>,
      children: (
        <div>
          {summary && (
            <Row gutter={16} style={{ marginBottom: 16 }}>
              <Col xs={12} sm={4}><Card><Statistic title="总字段" value={summary.total_fields} /></Card></Col>
              <Col xs={12} sm={4}><Card><Statistic title="分类覆盖率" value={summary.coverage_pct} suffix="%" valueStyle={{ color: summary.coverage_pct >= 90 ? '#3f8600' : '#cf1322' }} /></Card></Col>
              <Col xs={12} sm={4}><Card><Statistic title="已分类" value={summary.classified_count} /></Card></Col>
              <Col xs={12} sm={4}><Card><Statistic title="已分级" value={summary.tiered_count} /></Card></Col>
              <Col xs={12} sm={4}><Card><Statistic title="自动打标" value={summary.auto_tagged} /></Card></Col>
              <Col xs={12} sm={4}><Card><Statistic title="今日操作" value={summary.today_operations} /></Card></Col>
            </Row>
          )}
          <Card title="分类 × 分级 交叉矩阵" style={{ marginBottom: 16 }}>
            {categoryTier.length > 0 ? renderHeatmap() : <Text type="secondary">暂无数据</Text>}
          </Card>
          {gaps && (
            <Card title={<span><WarningOutlined /> 合规缺口 ({gaps.unclassified + gaps.low_confidence}个)</span>}>
              <Row gutter={16} style={{ marginBottom: 16 }}>
                <Col span={6}><Statistic title="未分类" value={gaps.unclassified} valueStyle={{ color: '#cf1322' }} /></Col>
                <Col span={6}><Statistic title="未分级" value={gaps.no_tier} valueStyle={{ color: '#cf1322' }} /></Col>
                <Col span={6}><Statistic title="低置信度" value={gaps.low_confidence} valueStyle={{ color: '#fa8c16' }} /></Col>
                <Col span={6}><Statistic title="异常字段" value={gaps.unmapped} valueStyle={{ color: '#fa8c16' }} /></Col>
              </Row>
              <Table columns={gapColumns} dataSource={gaps.gaps} rowKey="field_id"
                pagination={false} size="small" />
            </Card>
          )}
        </div>
      ),
    },
    {
      key: 'audit',
      label: <span><AuditOutlined /> 审计链路</span>,
      children: (
        <Card title="操作审计日志">
          <Table columns={auditColumns} dataSource={auditTrail.items} rowKey="id"
            loading={loading} size="small"
            pagination={{ total: auditTrail.total, pageSize: 50, showTotal: t => `共 ${t} 条` }} />
        </Card>
      ),
    },
    {
      key: 'history',
      label: <span><AuditOutlined /> 打标历史</span>,
      children: (
        <Card title="打标变更记录">
          <Table columns={historyColumns} dataSource={taggingHistory.items} rowKey="id"
            loading={loading} size="small"
            pagination={{ total: taggingHistory.total, pageSize: 50, showTotal: t => `共 ${t} 条` }} />
        </Card>
      ),
    },
  ]

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
        <div>
          <Title level={3} style={{ margin: 0 }}>合规审计</Title>
          <Text type="secondary">满足金融监管可追溯、可审计、可复现要求</Text>
        </div>
        <Button type="primary" icon={<DownloadOutlined />} onClick={exportComplianceReport}>
          导出合规报告
        </Button>
      </div>
      <Tabs defaultActiveKey="overview" items={tabItems} />
    </div>
  )
}
