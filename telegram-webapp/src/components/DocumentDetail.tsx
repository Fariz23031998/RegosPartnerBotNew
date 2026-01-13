import { useState, useEffect } from 'react'
import Loading from './Loading'
import ErrorMessage from './ErrorMessage'
import './DocumentDetail.css'

interface DocumentDetailProps {
  documentId: number
  documentType: 'purchase' | 'purchase-return' | 'wholesale' | 'wholesale-return'
  telegramUserId: number
  partnerId: number
  onBack: () => void
}

interface Operation {
  id: number
  item: {
    id: number
    name: string
  } | string
  quantity: number
  price?: number
  price2?: number
  cost?: number
  description?: string
}

function DocumentDetail({
  documentId,
  documentType,
  telegramUserId,
  partnerId,
  onBack
}: DocumentDetailProps) {
  const [document, setDocument] = useState<any>(null)
  const [operations, setOperations] = useState<Operation[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    fetchDocumentDetails()
  }, [documentId, documentType])

  const fetchDocumentDetails = async () => {
    setIsLoading(true)
    setError(null)

    try {
      let endpoint = ''
      switch (documentType) {
        case 'purchase':
          endpoint = `/api/telegram-webapp/documents/purchase/${documentId}`
          break
        case 'purchase-return':
          endpoint = `/api/telegram-webapp/documents/purchase-return/${documentId}`
          break
        case 'wholesale':
          endpoint = `/api/telegram-webapp/documents/wholesale/${documentId}`
          break
        case 'wholesale-return':
          endpoint = `/api/telegram-webapp/documents/wholesale-return/${documentId}`
          break
      }

      const url = `${endpoint}?telegram_user_id=${telegramUserId}&partner_id=${partnerId}`
      const response = await fetch(url)
      const data = await response.json()

      if (data.ok) {
        setDocument(data.document)
        setOperations(data.operations || [])
      } else {
        setError('Failed to fetch document details')
      }
    } catch (err) {
      setError('Error loading document details')
    } finally {
      setIsLoading(false)
    }
  }

  const formatDate = (date: number | string) => {
    if (typeof date === 'number') {
      return new Date(date * 1000).toLocaleDateString('ru-RU', {
        year: 'numeric',
        month: '2-digit',
        day: '2-digit',
        hour: '2-digit',
        minute: '2-digit'
      })
    }
    return new Date(date).toLocaleDateString('ru-RU', {
      year: 'numeric',
      month: '2-digit',
      day: '2-digit',
      hour: '2-digit',
      minute: '2-digit'
    })
  }

  const getDocumentTypeLabel = () => {
    switch (documentType) {
      case 'purchase':
        return 'Закупка'
      case 'purchase-return':
        return 'Возврат закупки'
      case 'wholesale':
        return 'Отгрузка'
      case 'wholesale-return':
        return 'Возврат отгрузки'
      default:
        return 'Документ'
    }
  }

  const useCost = documentType === 'purchase' || documentType === 'purchase-return'
  const isReturn = documentType === 'purchase-return' || documentType === 'wholesale-return'
  const [isExporting, setIsExporting] = useState(false)
  const [exportError, setExportError] = useState<string | null>(null)

  // Calculate total
  const total = operations.reduce((sum, op) => {
    const price = useCost ? (op.cost || 0) : (op.price || 0)
    return sum + (op.quantity * price)
  }, 0)

  const handleExport = async () => {
    setIsExporting(true)
    setExportError(null)

    try {
      let endpoint = ''
      switch (documentType) {
        case 'purchase':
          endpoint = `/api/telegram-webapp/documents/purchase/${documentId}/export`
          break
        case 'purchase-return':
          endpoint = `/api/telegram-webapp/documents/purchase-return/${documentId}/export`
          break
        case 'wholesale':
          endpoint = `/api/telegram-webapp/documents/wholesale/${documentId}/export`
          break
        case 'wholesale-return':
          endpoint = `/api/telegram-webapp/documents/wholesale-return/${documentId}/export`
          break
      }

      const url = `${endpoint}?telegram_user_id=${telegramUserId}&partner_id=${partnerId}`
      const response = await fetch(url, {
        method: 'POST'
      })
      const data = await response.json()

      if (data.ok) {
        // Show success message (could use Telegram WebApp.showAlert)
        const tg = window.Telegram?.WebApp
        if (tg) {
          tg.showAlert('Excel файл отправлен в ваш Telegram чат!')
        } else {
          alert('Excel файл отправлен в ваш Telegram чат!')
        }
      } else {
        setExportError(data.message || 'Ошибка при экспорте')
      }
    } catch (err) {
      setExportError('Ошибка при отправке файла')
    } finally {
      setIsExporting(false)
    }
  }

  if (isLoading) {
    return <Loading />
  }

  if (error) {
    return (
      <div>
        <ErrorMessage message={error} />
        <button onClick={onBack} className="back-button">Назад</button>
      </div>
    )
  }

  if (!document) {
    return (
      <div>
        <ErrorMessage message="Document not found" />
        <button onClick={onBack} className="back-button">Назад</button>
      </div>
    )
  }

  return (
    <div className="document-detail">
      <div className="document-header-section">
        <button onClick={onBack} className="back-button">← Назад</button>
        <div className="header-row">
          <h2>{getDocumentTypeLabel()}</h2>
          <button 
            onClick={handleExport} 
            className="export-button"
            disabled={isExporting}
          >
            {isExporting ? '⏳ Отправка...' : '📥 Скачать Excel'}
          </button>
        </div>
      </div>

      {exportError && (
        <div className="export-error">{exportError}</div>
      )}

      <div className="document-info">
        <div className="info-row">
          <span className="info-label">Номер документа:</span>
          <span className="info-value">{document.code || document.id}</span>
        </div>
        <div className="info-row">
          <span className="info-label">Дата:</span>
          <span className="info-value">{formatDate(document.date)}</span>
        </div>
        {document.stock && (
          <div className="info-row">
            <span className="info-label">Склад:</span>
            <span className="info-value">
              {typeof document.stock === 'object' ? document.stock.name : document.stock}
            </span>
          </div>
        )}
        {document.currency && (
          <div className="info-row">
            <span className="info-label">Валюта:</span>
            <span className="info-value">
              {typeof document.currency === 'object' ? document.currency.name : document.currency}
            </span>
          </div>
        )}
        {document.exchange_rate && document.exchange_rate !== 1 && document.exchange_rate !== '1' && document.exchange_rate !== 1.0 && (
          <div className="info-row">
            <span className="info-label">Курс обмена:</span>
            <span className="info-value">
              {typeof document.exchange_rate === 'number' 
                ? document.exchange_rate.toLocaleString('ru-RU', { 
                    minimumFractionDigits: 4, 
                    maximumFractionDigits: 4 
                  })
                : document.exchange_rate}
            </span>
          </div>
        )}
      </div>

      <div className="operations-section">
        <h3>Товары</h3>
        <div className="operations-list">
          {operations.length === 0 ? (
            <p className="no-items">Нет товаров</p>
          ) : (
            operations.map((op, idx) => {
              const itemName = typeof op.item === 'object' ? op.item.name : op.item || 'Неизвестный товар'
              const price = useCost ? (op.cost || 0) : (op.price || 0)
              const itemTotal = op.quantity * price

              return (
                <div key={op.id || idx} className="operation-item">
                  <div className="operation-header">
                    <span className="operation-number">{idx + 1}.</span>
                    <span className="operation-name">{itemName}</span>
                  </div>
                  <div className="operation-details">
                    <div className="operation-line">
                      {op.quantity} × {price.toLocaleString('ru-RU', { 
                        minimumFractionDigits: 2, 
                        maximumFractionDigits: 2 
                      })} = {itemTotal.toLocaleString('ru-RU', { 
                        minimumFractionDigits: 2, 
                        maximumFractionDigits: 2 
                      })}
                    </div>
                    {op.description && (
                      <div className="operation-description">{op.description}</div>
                    )}
                  </div>
                </div>
              )
            })
          )}
        </div>
      </div>

      <div className="document-total">
        <div className="total-row">
          <span className="total-label">Всего товаров:</span>
          <span className="total-value">
            {operations.reduce((sum, op) => sum + op.quantity, 0)}
          </span>
        </div>
        <div className="total-row">
          <span className="total-label">Итого к оплате:</span>
          <span className="total-value total-amount">
            {total.toLocaleString('ru-RU', { 
              minimumFractionDigits: 2, 
              maximumFractionDigits: 2 
            })}
            {document.currency && (
              <span className="currency">
                {' '}{typeof document.currency === 'object' ? document.currency.name : document.currency}
              </span>
            )}
          </span>
        </div>
        {document.exchange_rate && document.exchange_rate !== 1 && document.exchange_rate !== '1' && document.exchange_rate !== 1.0 && (
          <div className="total-row">
            <span className="total-label">Курс обмена:</span>
            <span className="total-value">
              {typeof document.exchange_rate === 'number' 
                ? document.exchange_rate.toLocaleString('ru-RU', { 
                    minimumFractionDigits: 4, 
                    maximumFractionDigits: 4 
                  })
                : document.exchange_rate}
            </span>
          </div>
        )}
      </div>
    </div>
  )
}

export default DocumentDetail
