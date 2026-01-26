import { useState, useEffect } from 'react'
import { FaArrowLeft } from 'react-icons/fa'
import Loading from './Loading'
import ErrorMessage from './ErrorMessage'
import { apiFetch } from '../utils/api'
import { formatNumber } from '../utils/formatNumber'
import './DocumentDetail.css'
import { useLanguage } from '../contexts/LanguageContext'
import { languageService } from '../utils/language'

interface DocumentDetailProps {
  documentId: number
  documentType: 'purchase' | 'purchase-return' | 'wholesale' | 'wholesale-return'
  telegramUserId: number
  partnerId: number
  botName: string | null
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
  botName,
  onBack
}: DocumentDetailProps) {
  const [document, setDocument] = useState<any>(null)
  const [operations, setOperations] = useState<Operation[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const { t } = useLanguage()
  
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
          endpoint = `/telegram-webapp/documents/purchase/${documentId}`
          break
        case 'purchase-return':
          endpoint = `/telegram-webapp/documents/purchase-return/${documentId}`
          break
        case 'wholesale':
          endpoint = `/telegram-webapp/documents/wholesale/${documentId}`
          break
        case 'wholesale-return':
          endpoint = `/telegram-webapp/documents/wholesale-return/${documentId}`
          break
      }

      // SECURITY: bot_name is REQUIRED
      if (!botName) {
        setError(t('document-detail.error.bot-name-required', 'Bot name is required. Please refresh the page.'))
        setIsLoading(false)
        return
      }
      
      const url = new URL(endpoint, window.location.origin)
      url.searchParams.set('telegram_user_id', telegramUserId.toString())
      url.searchParams.set('partner_id', partnerId.toString())
      url.searchParams.set('bot_name', botName) // REQUIRED
      
      const response = await apiFetch(url.pathname + url.search)
      const data = await response.json()

      if (data.ok) {
        setDocument(data.document)
        setOperations(data.operations || [])
      } else {
        setError(t('document-detail.error.fetch-details', 'Failed to fetch document details'))
      }
    } catch (err) {
      setError(t('document-detail.error.load-details', 'Error loading document details'))
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
    // Map system document types to partner perspective
    switch (documentType) {
      case 'purchase':
        return t('document-detail.type.shipment', 'Отгрузка')  // System purchase -> Partner sees shipment
      case 'purchase-return':
        return t('document-detail.type.shipment-return', 'Возврат отгрузки')  // System purchase return -> Partner sees shipment return
      case 'wholesale':
        return t('document-detail.type.purchase', 'Закупка')  // System wholesale -> Partner sees purchase
      case 'wholesale-return':
        return t('document-detail.type.purchase-return', 'Возврат закупки')  // System wholesale return -> Partner sees purchase return
      default:
        return t('document-detail.type.document', 'Документ')
    }
  }

  const useCost = documentType === 'purchase' || documentType === 'purchase-return'
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
          endpoint = `/telegram-webapp/documents/purchase/${documentId}/export`
          break
        case 'purchase-return':
          endpoint = `/telegram-webapp/documents/purchase-return/${documentId}/export`
          break
        case 'wholesale':
          endpoint = `/telegram-webapp/documents/wholesale/${documentId}/export`
          break
        case 'wholesale-return':
          endpoint = `/telegram-webapp/documents/wholesale-return/${documentId}/export`
          break
      }

      // SECURITY: bot_name is REQUIRED
      if (!botName) {
        setExportError(t('document-detail.export.error.bot-name-required', 'Bot name is required. Please refresh the page.'))
        setIsExporting(false)
        return
      }
      
      const url = new URL(endpoint, window.location.origin)
      const currentLanguage = languageService.getCurrentLanguage()
      url.searchParams.set('telegram_user_id', telegramUserId.toString())
      url.searchParams.set('partner_id', partnerId.toString())
      url.searchParams.set('bot_name', botName) // REQUIRED
      url.searchParams.set('lang_code', currentLanguage)
      
      const response = await apiFetch(url.pathname + url.search, {
        method: 'POST'
      })
      const data = await response.json()

      if (data.ok) {
        // Show success message (could use Telegram WebApp.showAlert)
        const tg = window.Telegram?.WebApp
        if (tg) {
          tg.showAlert(t('document-detail.export.success', 'Excel файл отправлен в ваш Telegram чат!'))
        } else {
          alert(t('document-detail.export.success', 'Excel файл отправлен в ваш Telegram чат!'))
        }
      } else {
        setExportError(data.message || t('document-detail.export.error', 'Ошибка при экспорте'))
      }
    } catch (err) {
      setExportError(t('document-detail.export.error', 'Ошибка при отправке файла'))
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
        <button onClick={onBack} className="back-button-icon" aria-label="Назад">
          <FaArrowLeft />
        </button>
      </div>
    )
  }

  if (!document) {
    return (
      <div>
        <ErrorMessage message={t('document-detail.error.not-found', "Document not found")} />
        <button onClick={onBack} className="back-button-icon" aria-label="Назад">
          <FaArrowLeft />
        </button>
      </div>
    )
  }

  return (
    <div className="document-detail">
      <div className="document-header-section">
        <button onClick={onBack} className="back-button-icon" aria-label="Назад">
          <FaArrowLeft />
        </button>
        <div className="header-row">
          <h2>{getDocumentTypeLabel()}</h2>
          <button 
            onClick={handleExport} 
            className="export-button"
            disabled={isExporting}
          >
            {isExporting ? t('document-detail.export.submitting', '⏳ Отправка...') : t('document-detail.export.download', '📥 Скачать Excel')}
          </button>
        </div>
      </div>

      {exportError && (
        <div className="export-error">{exportError}</div>
      )}

      <div className="document-info">
        <div className="info-row">
          <span className="info-label">{t('document-detail.info.number', 'Номер документа:')}</span>
          <span className="info-value">{document.code || document.id}</span>
        </div>
        <div className="info-row">
          <span className="info-label">{t('document-detail.info.date', 'Дата:')}</span>
          <span className="info-value">{formatDate(document.date)}</span>
        </div>
        {document.stock && (
          <div className="info-row">
            <span className="info-label">{t('document-detail.info.stock', 'Склад:')}</span>
            <span className="info-value">
              {typeof document.stock === 'object' ? document.stock.name : document.stock}
            </span>
          </div>
        )}
        {document.currency && (
          <div className="info-row">
            <span className="info-label">{t('document-detail.info.currency', 'Валюта:')}</span>
            <span className="info-value">
              {typeof document.currency === 'object' ? document.currency.name : document.currency}
            </span>
          </div>
        )}
        {document.exchange_rate && document.exchange_rate !== 1 && document.exchange_rate !== '1' && document.exchange_rate !== 1.0 && (
          <div className="info-row">
            <span className="info-label">{t('document-detail.info.exchange-rate', 'Курс обмена:')}</span>
            <span className="info-value">
              {typeof document.exchange_rate === 'number' 
                ? formatNumber(document.exchange_rate, 4)
                : document.exchange_rate}
            </span>
          </div>
        )}
      </div>

      <div className="operations-section">
        <h3>{t('document-detail.operations.title', 'Товары')}</h3>
        <div className="operations-list">
          {operations.length === 0 ? (
            <p className="no-items">{t('document-detail.operations.no-items', 'Нет товаров')}</p>
          ) : (
            operations.map((op, idx) => {
              const itemName = typeof op.item === 'object' ? op.item.name : op.item || t('document-detail.operations.unknown-item', 'Неизвестный товар')
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
                      {formatNumber(op.quantity)} × {formatNumber(price)} = {formatNumber(itemTotal)}
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
          <span className="total-label">{t('document-detail.total.total-items', 'Всего товаров:')}</span>
          <span className="total-value">
            {operations.reduce((sum, op) => sum + op.quantity, 0)}
          </span>
        </div>
        <div className="total-row">
          <span className="total-label">{t("document-detail.total.total-payment", "Итого к оплате:")}</span>
          <span className="total-value total-amount">
            {formatNumber(total)}
            {document.currency && (
              <span className="currency">
                {' '}{typeof document.currency === 'object' ? document.currency.name : document.currency}
              </span>
            )}
          </span>
        </div>
        {document.exchange_rate && document.exchange_rate !== 1 && document.exchange_rate !== '1' && document.exchange_rate !== 1.0 && (
          <div className="total-row">
            <span className="total-label">{t("document-detail.total.exchange-rate", "Курс обмена:")}</span>
            <span className="total-value">
              {typeof document.exchange_rate === 'number' 
                ? formatNumber(document.exchange_rate, 4)
                : document.exchange_rate}
            </span>
          </div>
        )}
      </div>
    </div>
  )
}

export default DocumentDetail
