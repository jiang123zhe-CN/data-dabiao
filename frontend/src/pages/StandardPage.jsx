import { useState, useEffect, useCallback } from 'react'
import {
  Row, Col, Card, Typography, Button, Space, message, Popconfirm, Spin, Empty,
  Tabs, Table, Tag, Drawer, Form, Input, Select, InputNumber, Upload, Divider,
} from 'antd'
import {
  PlusOutlined, EditOutlined, DeleteOutlined, DownloadOutlined, UploadOutlined,
  SafetyOutlined, ApartmentOutlined,
} from '@ant-design/icons'
import buildTree from '../utils/buildTree'
import {
  getCategoryTree, getCategories, getCategory,
  createCategory, updateCategory, deleteCategory,
  exportCategories, importCategories,
  getTiers, createTier, updateTier, deleteTier,
  exportTiers, importTiers,
} from '../services/standardService'
import { useAuth } from '../hooks/useAuth'

const { Title, Text } = Typography
const { TextArea } = Input
const { Option } = Select

// ── Tier level color mapping ──
const TIER_COLORS = { L1: 'green', L2: 'blue', L3: 'orange', L4: 'red' }
const TIER_NAMES = { L1: '公开', L2: '内部', L3: '敏感', L4: '机密/严格保密' }
const CATEGORY_TYPES = [
  { value: 'business', label: '业务分类' },
  { value: 'regulatory', label: '监管分类' },
  { value: 'technical', label: '技术分类' },
]

// ══════════════════════════════════════════════════════════════════
// Categories Tab
// ══════════════════════════════════════════════════════════════════

function CategoriesTab({ canEdit }) {
  const [flatList, setFlatList] = useState([])
  const [selectedId, setSelectedId] = useState(null)
  const [selectedCat, setSelectedCat] = useState(null)
  const [mode, setMode] = useState('view')
  const [parentCat, setParentCat] = useState(null)
  const [loading, setLoading] = useState(false)
  const [submitting, setSubmitting] = useState(false)
  const [form] = Form.useForm()

  const treeData = buildTree(flatList)

  const loadTree = useCallback(async () => {
    setLoading(true)
    try {
      const data = await getCategoryTree()
      setFlatList(data)
    } catch {
      message.error('加载分类标准失败')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => { loadTree() }, [loadTree])

  const loadDetail = async (id) => {
    try {
      const data = await getCategory(id)
      setSelectedCat(data)
      setMode('view')
      setParentCat(null)
    } catch {
      message.error('加载分类详情失败')
    }
  }

  const handleSelect = (id) => {
    setSelectedId(id)
    loadDetail(id)
  }

  const handleCreate = (parentData = null) => {
    setSelectedCat(null)
    setParentCat(parentData)
    setMode('create')
    form.resetFields()
    if (parentData) form.setFieldsValue({ parent_id: parentData.id })
  }

  const handleEdit = () => {
    setMode('edit')
    form.setFieldsValue({
      name: selectedCat?.name,
      code: selectedCat?.code,
      category_type: selectedCat?.category_type,
      description: selectedCat?.description,
      keywords: selectedCat?.keywords,
      regulatory_ref: selectedCat?.regulatory_ref,
      sort_order: selectedCat?.sort_order,
    })
  }

  const handleDelete = async () => {
    try {
      await deleteCategory(selectedId)
      message.success('分类已删除')
      setSelectedId(null)
      setSelectedCat(null)
      setMode('view')
      loadTree()
    } catch (err) {
      message.error(err.response?.data?.detail || '删除失败')
    }
  }

  const handleSubmit = async () => {
    const values = await form.validateFields()
    setSubmitting(true)
    try {
      if (mode === 'edit') {
        await updateCategory(selectedId, values)
        message.success('分类已更新')
        loadDetail(selectedId)
      } else {
        await createCategory(values)
        message.success('分类已创建')
        setMode('view')
        setParentCat(null)
        loadTree()
      }
    } catch (err) {
      message.error(err.response?.data?.detail || '操作失败')
    } finally {
      setSubmitting(false)
    }
  }

  const handleCancel = () => {
    if (selectedCat) {
      setMode('view')
      setParentCat(null)
    } else {
      setSelectedCat(null)
      setMode('view')
      setParentCat(null)
    }
  }

  const handleImport = async (info) => {
    const file = info.file
    if (!file) return
    try {
      const res = await importCategories(file)
      message.success(`导入完成: 新增 ${res.created} 条`)
      if (res.errors?.length) {
        message.warning(`${res.errors.length} 条记录导入失败`)
      }
      loadTree()
    } catch {
      message.error('导入失败')
    }
  }

  const renderCategoryTypeTag = (type) => {
    const map = { business: { color: 'blue', label: '业务' }, regulatory: { color: 'gold', label: '监管' }, technical: { color: 'default', label: '技术' } }
    const cfg = map[type] || { color: 'default', label: type }
    return <Tag color={cfg.color}>{cfg.label}</Tag>
  }

  // For the tree display, use antd Tree component
  const renderTree = (nodes) => {
    if (!nodes || nodes.length === 0) return null
    return nodes.map(node => ({
      key: node.id,
      title: <span>{node.name} {renderCategoryTypeTag(node.category_type)}</span>,
      children: node.children?.length ? renderTree(node.children) : undefined,
    }))
  }

  const treeSelectData = renderTree(treeData)

  return (
    <Row gutter={16}>
      <Col xs={24} md={7}>
        <Card
          title="分类结构"
          extra={
            canEdit && (
              <Space size="small">
                <Upload accept=".xlsx,.xls" showUploadList={false} customRequest={({ file }) => handleImport({ file })}>
                  <Button size="small" icon={<UploadOutlined />} />
                </Upload>
                <Button size="small" icon={<DownloadOutlined />} onClick={exportCategories} />
                <Button size="small" type="primary" icon={<PlusOutlined />} onClick={() => handleCreate()}>
                  新建
                </Button>
              </Space>
            )
          }
          style={{ height: 'calc(100vh - 230px)', overflow: 'auto' }}
        >
          {loading ? <Spin /> : treeData.length === 0 ? (
            <Empty description="暂无分类标准，请创建或导入" />
          ) : (
            <div>
              {flatList.map(cat => {
                const indent = cat.level * 20
                return (
                  <div
                    key={cat.id}
                    onClick={() => handleSelect(cat.id)}
                    style={{
                      padding: '6px 12px', margin: '2px 0', cursor: 'pointer',
                      borderRadius: 6, marginLeft: indent,
                      background: selectedId === cat.id ? '#e6f4ff' : 'transparent',
                      fontWeight: cat.level === 0 ? 500 : 400,
                    }}
                  >
                    <ApartmentOutlined style={{ marginRight: 6, color: cat.level === 0 ? '#1677ff' : '#999' }} />
                    {cat.name}
                    {renderCategoryTypeTag(cat.category_type)}
                  </div>
                )
              })}
            </div>
          )}
        </Card>
      </Col>
      <Col xs={24} md={17}>
        <Card
          title={
            mode === 'create'
              ? parentCat ? `添加子分类: ${parentCat.name}` : '新建根分类'
              : mode === 'edit' ? '编辑分类' : '分类详情'
          }
          extra={
            mode === 'view' && selectedCat && canEdit && (
              <Space>
                <Button icon={<PlusOutlined />} onClick={() => handleCreate(selectedCat)}>添加子分类</Button>
                <Button icon={<EditOutlined />} onClick={handleEdit}>编辑</Button>
                <Popconfirm title="确定删除此分类？有子分类时不可删除" onConfirm={handleDelete}>
                  <Button danger icon={<DeleteOutlined />}>删除</Button>
                </Popconfirm>
              </Space>
            )
          }
        >
          {mode === 'view' && selectedCat ? (
            <div>
              <p><Text strong>名称：</Text>{selectedCat.name}</p>
              <p><Text strong>编码：</Text><Tag>{selectedCat.code}</Tag></p>
              <p><Text strong>分类类型：</Text>{renderCategoryTypeTag(selectedCat.category_type)}</p>
              <p><Text strong>层级：</Text>{selectedCat.level}</p>
              <p><Text strong>版本：</Text>{selectedCat.version}</p>
              <p><Text strong>描述：</Text>{selectedCat.description || '-'}</p>
              <p><Text strong>关键词：</Text>{selectedCat.keywords || '-'}</p>
              <p><Text strong>法规依据：</Text>{selectedCat.regulatory_ref || '-'}</p>
              <p><Text strong>排序：</Text>{selectedCat.sort_order}</p>
            </div>
          ) : mode === 'view' && !selectedCat ? (
            <Empty description="请从左侧选择一个分类" />
          ) : (
            <Form form={form} layout="vertical" onFinish={handleSubmit}>
              <Form.Item name="name" label="名称" rules={[{ required: true, message: '请输入名称' }]}>
                <Input maxLength={200} />
              </Form.Item>
              <Form.Item name="code" label="编码" rules={[{ required: true, message: '请输入编码' }]}>
                <Input maxLength={100} />
              </Form.Item>
              <Form.Item name="parent_id" label="父级分类">
                <Select allowClear placeholder="留空为根分类">
                  {flatList.map(c => (
                    <Option key={c.id} value={c.id} disabled={c.id === selectedId}>
                      {'　'.repeat(c.level)}{c.name}
                    </Option>
                  ))}
                </Select>
              </Form.Item>
              <Form.Item name="category_type" label="分类类型" initialValue="business">
                <Select options={CATEGORY_TYPES} />
              </Form.Item>
              <Form.Item name="keywords" label="关键词">
                <Input placeholder="逗号分隔" />
              </Form.Item>
              <Form.Item name="description" label="描述">
                <TextArea rows={2} />
              </Form.Item>
              <Form.Item name="regulatory_ref" label="法规依据">
                <Input placeholder="如 金融数据安全分级指南 JR/T 0197-2020" />
              </Form.Item>
              <Form.Item name="sort_order" label="排序" initialValue={0}>
                <InputNumber min={0} />
              </Form.Item>
              <Space>
                <Button type="primary" htmlType="submit" loading={submitting}>
                  {mode === 'edit' ? '保存' : '创建'}
                </Button>
                <Button onClick={handleCancel}>取消</Button>
              </Space>
            </Form>
          )}
        </Card>
      </Col>
    </Row>
  )
}

// ══════════════════════════════════════════════════════════════════
// Tiers Tab
// ══════════════════════════════════════════════════════════════════

function TiersTab({ canEdit }) {
  const [tiers, setTiers] = useState([])
  const [loading, setLoading] = useState(false)
  const [drawerOpen, setDrawerOpen] = useState(false)
  const [editingTier, setEditingTier] = useState(null)
  const [submitting, setSubmitting] = useState(false)
  const [form] = Form.useForm()

  const load = useCallback(async () => {
    setLoading(true)
    try {
      const data = await getTiers()
      setTiers(data)
    } catch {
      message.error('加载分级规则失败')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => { load() }, [load])

  const handleAdd = () => {
    setEditingTier(null)
    form.resetFields()
    form.setFieldsValue({ rule_type: 'keyword', priority: 0, version: 'v1.0' })
    setDrawerOpen(true)
  }

  const handleEdit = (record) => {
    setEditingTier(record)
    form.setFieldsValue(record)
    setDrawerOpen(true)
  }

  const handleDelete = async (id) => {
    try {
      await deleteTier(id)
      message.success('规则已删除')
      load()
    } catch (err) {
      message.error(err.response?.data?.detail || '删除失败')
    }
  }

  const handleSubmit = async () => {
    const values = await form.validateFields()
    setSubmitting(true)
    try {
      if (editingTier) {
        await updateTier(editingTier.id, values)
        message.success('规则已更新')
      } else {
        await createTier(values)
        message.success('规则已创建')
      }
      setDrawerOpen(false)
      load()
    } catch (err) {
      message.error(err.response?.data?.detail || '操作失败')
    } finally {
      setSubmitting(false)
    }
  }

  const handleImport = async (info) => {
    const file = info.file
    if (!file) return
    try {
      const res = await importTiers(file)
      message.success(`导入完成: 新增 ${res.created} 条`)
      load()
    } catch {
      message.error('导入失败')
    }
  }

  const columns = [
    { title: '级别', dataIndex: 'tier_level', key: 'tier_level', width: 80,
      render: (v) => <Tag color={TIER_COLORS[v]}>{v}</Tag> },
    { title: '名称', dataIndex: 'tier_name', key: 'tier_name', width: 120 },
    { title: '规则类型', dataIndex: 'rule_type', key: 'rule_type', width: 100,
      render: (v) => {
        const labels = { keyword: '关键词', regex: '正则', metadata: '元数据' }
        return <Tag>{labels[v] || v}</Tag>
      }},
    { title: '规则内容', dataIndex: 'rule_content', key: 'rule_content', ellipsis: true,
      render: (v) => {
        try {
          const obj = JSON.parse(v)
          return <Text style={{ fontSize: 12 }}>{JSON.stringify(obj).substring(0, 80)}...</Text>
        } catch { return <Text style={{ fontSize: 12 }}>{v?.substring(0, 80)}</Text> }
      }},
    { title: '优先级', dataIndex: 'priority', key: 'priority', width: 80 },
    { title: '法规依据', dataIndex: 'regulatory_basis', key: 'regulatory_basis', ellipsis: true, width: 200 },
    { title: '版本', dataIndex: 'version', key: 'version', width: 80 },
    ...(canEdit ? [{
      title: '操作', key: 'actions', width: 120,
      render: (_, record) => (
        <Space>
          <Button size="small" icon={<EditOutlined />} onClick={() => handleEdit(record)}>编辑</Button>
          <Popconfirm title="确定删除此规则？" onConfirm={() => handleDelete(record.id)}>
            <Button size="small" danger icon={<DeleteOutlined />}>删除</Button>
          </Popconfirm>
        </Space>
      ),
    }] : []),
  ]

  return (
    <div>
      <div style={{ marginBottom: 16, display: 'flex', justifyContent: 'space-between' }}>
        <Space>
          <SafetyOutlined /> 共 {tiers.length} 条分级规则
        </Space>
        {canEdit && (
          <Space>
            <Upload accept=".xlsx,.xls" showUploadList={false} customRequest={({ file }) => handleImport({ file })}>
              <Button icon={<UploadOutlined />}>导入</Button>
            </Upload>
            <Button icon={<DownloadOutlined />} onClick={exportTiers}>导出</Button>
            <Button type="primary" icon={<PlusOutlined />} onClick={handleAdd}>新建规则</Button>
          </Space>
        )}
      </div>
      <Table
        columns={columns}
        dataSource={tiers}
        rowKey="id"
        loading={loading}
        pagination={false}
      />
      <Drawer
        title={editingTier ? '编辑分级规则' : '新建分级规则'}
        open={drawerOpen}
        onClose={() => setDrawerOpen(false)}
        width={560}
        extra={
          <Space>
            <Button onClick={() => setDrawerOpen(false)}>取消</Button>
            <Button type="primary" onClick={handleSubmit} loading={submitting}>保存</Button>
          </Space>
        }
      >
        <Form form={form} layout="vertical">
          <Form.Item name="tier_level" label="分级级别" rules={[{ required: true }]}>
            <Select>
              <Option value="L1">L1 - 公开</Option>
              <Option value="L2">L2 - 内部</Option>
              <Option value="L3">L3 - 敏感</Option>
              <Option value="L4">L4 - 机密/严格保密</Option>
            </Select>
          </Form.Item>
          <Form.Item name="tier_name" label="分级名称" rules={[{ required: true }]}>
            <Input />
          </Form.Item>
          <Form.Item name="rule_type" label="规则类型" rules={[{ required: true }]}>
            <Select>
              <Option value="keyword">关键词匹配</Option>
              <Option value="regex">正则表达式</Option>
              <Option value="metadata">元数据匹配</Option>
            </Select>
          </Form.Item>
          <Form.Item name="rule_content" label="规则内容(JSON)" rules={[{ required: true }]}
            extra='JSON格式: {"keywords":["关键词1","关键词2"],"patterns":["正则1"],"metadata_rules":{}}'>
            <TextArea rows={6} />
          </Form.Item>
          <Form.Item name="priority" label="优先级">
            <InputNumber min={0} max={100} />
          </Form.Item>
          <Form.Item name="regulatory_basis" label="法规依据">
            <Input placeholder="如《个人信息保护法》第28条" />
          </Form.Item>
          <Form.Item name="version" label="版本" initialValue="v1.0">
            <Input />
          </Form.Item>
        </Form>
      </Drawer>
    </div>
  )
}

// ══════════════════════════════════════════════════════════════════
// Main Page
// ══════════════════════════════════════════════════════════════════

export default function StandardPage() {
  const { hasRole } = useAuth()
  const canEdit = hasRole('system_admin', 'admin')

  const tabItems = [
    {
      key: 'categories',
      label: <span><ApartmentOutlined /> 分类标准</span>,
      children: <CategoriesTab canEdit={canEdit} />,
    },
    {
      key: 'tiers',
      label: <span><SafetyOutlined /> 分级规则</span>,
      children: <TiersTab canEdit={canEdit} />,
    },
  ]

  return (
    <div>
      <Title level={3}>标准管理</Title>
      <Text type="secondary" style={{ marginBottom: 16, display: 'block' }}>
        中国金融行业数据分类分级标准 — 支持标准模板导入/导出，快速适配监管要求
      </Text>
      <Tabs defaultActiveKey="categories" items={tabItems} />
    </div>
  )
}
