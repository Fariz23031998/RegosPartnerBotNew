import { useState, useEffect } from 'react'
import { FaArrowLeft } from 'react-icons/fa'
import DocumentCard from './DocumentCard'
import DocumentDetail from './DocumentDetail'
import PartnerBalance from './PartnerBalance'
import { apiFetch } from '../utils/api'
import { formatNumber } from '../utils/formatNumber'
import './DocumentList.css'
import { useLanguage } from '../contexts/LanguageContext'

interface Document {
  id: number
  code: string
  date: number | string
  total?: number
  [key: string]: any
}

interface DocumentListProps {
  telegramUserId: number
  partnerId: number
  botName: string | null
  onBack?: () => void
}

type DocumentType = 'wholesale' | 'wholesale-return' | 'purchase' | 'purchase-return' | 'payment' | 'balance'

interface DocumentTotals {
  [documentType: string]: {
    [currency: string]: number
  }
}

function DocumentList({ telegramUserId, partnerId, botName, onBack }: DocumentListProps) {
  const [activeTab, setActiveTab] = useState<DocumentType>('wholesale')
  const [documents, setDocuments] = useState<Document[]>([])
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [selectedDocument, setSelectedDocument] = useState<{ id: number; type: 'wholesale' | 'wholesale-return' | 'purchase' | 'purchase-return' } | null>(null)
  const [showDatePicker, setShowDatePicker] = useState(false)
  const [documentTotals, setDocumentTotals] = useState<DocumentTotals>({})
  const [showTotalsSection, setShowTotalsSection] = useState(false)
  const { t } = useLanguage()
  // Set default dates to current month
  const getCurrentMonthDates = () => {
    const now = new Date()
    const year = now.getFullYear()
    const month = now.getMonth()
    const firstDay = new Date(year, month, 1)
    const lastDay = new Date(year, month + 1, 0)

    return {
      start: firstDay.toISOString().split('T')[0],
      end: lastDay.toISOString().split('T')[0]
    }
  }

  // Date picker state (temporary, for UI)
  const [startDate, setStartDate] = useState(getCurrentMonthDates().start)
  const [endDate, setEndDate] = useState(getCurrentMonthDates().end)
  
  // Applied dates (used for fetching data)
  const [appliedStartDate, setAppliedStartDate] = useState(getCurrentMonthDates().start)
  const [appliedEndDate, setAppliedEndDate] = useState(getCurrentMonthDates().end)

  useEffect(() => {
    // Only fetch if botName is available
    // Use applied dates, not the picker dates
    if (botName) {
      fetchDocuments()
      fetchAllDocumentTotals()
    }
  }, [activeTab, telegramUserId, partnerId, appliedStartDate, appliedEndDate, botName])

  // Helper function to get currency from a document
  const getCurrencyFromDocument = (doc: Document, docType: DocumentType): string => {
    if (docType === 'payment') {
      // For payment documents, currency is in type.account.currency
      if (doc.type?.account?.currency) {
        return typeof doc.type.account.currency === 'object'
          ? doc.type.account.currency.name || t('document-list.currency.unknown', 'Unknown')
          : t('document-list.currency.unknown', 'Unknown')
      }
    } else {
      // For other documents, currency is directly on the document
      if (doc.currency) {
        return typeof doc.currency === 'object'
          ? doc.currency.name || t('document-list.currency.unknown', 'Unknown')
          : t('document-list.currency.unknown', 'Unknown')
      }
    }
    return t('document-list.currency.unknown', 'Unknown')
  }

  // Helper function to get amount from a document
  const getAmountFromDocument = (doc: Document, docType: DocumentType): number => {
    if (docType === 'payment') {
      return doc.amount || 0
    }
    return doc.total || doc.total_amount || doc.amount || 0
  }

  // Fetch totals for all document types
  const fetchAllDocumentTotals = async () => {
    const types: DocumentType[] = ['purchase', 'purchase-return', 'wholesale', 'wholesale-return', 'payment']
    const totals: DocumentTotals = {}

    try {
      await Promise.all(types.map(async (type) => {
        let endpoint = ''
        switch (type) {
          case 'purchase':
            endpoint = '/telegram-webapp/documents/purchase'
            break
          case 'purchase-return':
            endpoint = '/telegram-webapp/documents/purchase-return'
            break
          case 'wholesale':
            endpoint = '/telegram-webapp/documents/wholesale'
            break
          case 'wholesale-return':
            endpoint = '/telegram-webapp/documents/wholesale-return'
            break
          case 'payment':
            endpoint = '/telegram-webapp/documents/payment'
            break
        }

        // SECURITY: bot_name is REQUIRED
        if (!botName) {
          console.error('bot_name is required but not available')
          return
        }
        
        const url = new URL(endpoint, window.location.origin)
        url.searchParams.set('telegram_user_id', telegramUserId.toString())
        url.searchParams.set('partner_id', partnerId.toString())
        url.searchParams.set('start_date', appliedStartDate) // Use applied dates
        url.searchParams.set('end_date', appliedEndDate) // Use applied dates
        url.searchParams.set('bot_name', botName) // REQUIRED
        
        const response = await apiFetch(url.pathname + url.search)
        const data = await response.json()

        if (data.ok) {
          let docs: Document[] = []
          if (type === 'payment') {
            docs = [
              ...(data.documents.income || []),
              ...(data.documents.outcome || [])
            ]
          } else {
            docs = data.documents || []
          }

          // Calculate totals by currency
          const typeTotals: { [currency: string]: number } = {}
          docs.forEach((doc: Document) => {
            const currency = getCurrencyFromDocument(doc, type)
            const amount = getAmountFromDocument(doc, type)
            typeTotals[currency] = (typeTotals[currency] || 0) + amount
          })

          totals[type] = typeTotals
        }
      }))

      setDocumentTotals(totals)
    } catch (err) {
      console.error('Error fetching document totals:', err)
    }
  }

  // Close date picker when clicking outside
  useEffect(() => {
    if (!showDatePicker) return

    const handleClickOutside = (event: MouseEvent) => {
      const target = event.target as HTMLElement
      if (!target.closest('.date-filter-section')) {
        setShowDatePicker(false)
      }
    }

    document.addEventListener('mousedown', handleClickOutside)
    return () => {
      document.removeEventListener('mousedown', handleClickOutside)
    }
  }, [showDatePicker])

  const fetchDocuments = async () => {
    // SECURITY: bot_name is REQUIRED
    if (!botName) {
      setError(t('document-list.error.bot-name-required', 'Bot name is required. Please refresh the page.'))
      setIsLoading(false)
      return
    }
    
    setIsLoading(true)
    setError(null)

    try {
      let endpoint = ''
      switch (activeTab) {
        case 'purchase':
          endpoint = '/telegram-webapp/documents/purchase'
          break
        case 'purchase-return':
          endpoint = '/telegram-webapp/documents/purchase-return'
          break
        case 'wholesale':
          endpoint = '/telegram-webapp/documents/wholesale'
          break
        case 'wholesale-return':
          endpoint = '/telegram-webapp/documents/wholesale-return'
          break
        case 'payment':
          endpoint = '/telegram-webapp/documents/payment'
          break
      }

      const url = new URL(endpoint, window.location.origin)
      url.searchParams.set('telegram_user_id', telegramUserId.toString())
      url.searchParams.set('partner_id', partnerId.toString())
      url.searchParams.set('start_date', startDate)
      url.searchParams.set('end_date', endDate)
      url.searchParams.set('bot_name', botName) // REQUIRED
      
      const response = await apiFetch(url.pathname + url.search)
      const data = await response.json()

      if (data.ok) {
        if (activeTab === 'payment') {
          // Payment documents have income and outcome arrays
          const allPayments = [
            ...(data.documents.income || []),
            ...(data.documents.outcome || [])
          ]
          setDocuments(allPayments)
        } else {
          setDocuments(data.documents || [])
        }
      } else {
        setError(t('document-list.error.fetch-documents', 'Failed to fetch documents'))
      }
    } catch (err) {
      setError(t('document-list.error.load-documents', 'Error loading documents'))
    } finally {
      setIsLoading(false)
    }
  }

  const formatDate = (date: number | string) => {
    if (typeof date === 'number') {
      return new Date(date * 1000).toLocaleDateString('ru-RU')
    }
    return new Date(date).toLocaleDateString('ru-RU')
  }

  // If a document is selected, show detail view
  if (selectedDocument) {
    return (
      <DocumentDetail
        documentId={selectedDocument.id}
        documentType={selectedDocument.type}
        telegramUserId={telegramUserId}
        partnerId={partnerId}
        botName={botName}
        onBack={() => setSelectedDocument(null)}
      />
    )
  }

  const handleDateChange = () => {
    if (startDate && endDate && startDate <= endDate) {
      // Apply the selected dates - this will trigger useEffect to fetch data
      setAppliedStartDate(startDate)
      setAppliedEndDate(endDate)
      setShowDatePicker(false)
    }
  }

  const resetToCurrentMonth = () => {
    const dates = getCurrentMonthDates()
    setStartDate(dates.start)
    setEndDate(dates.end)
    // Apply the reset dates immediately
    setAppliedStartDate(dates.start)
    setAppliedEndDate(dates.end)
    setShowDatePicker(false)
  }

  return (
    <div className="document-list">
      {onBack && (
        <div className="document-list-header">
          <button className="back-button-icon" onClick={onBack} aria-label="Назад">
            <FaArrowLeft />
          </button>
        </div>
      )}
      <div className="header-section">
        <div className="tabs">
          <button
            className={activeTab === 'wholesale' ? 'active' : ''}
            onClick={() => setActiveTab('wholesale')}
          >
            {t('document-list.tabs.purchase', 'Закупки')}
          </button>
          <button
            className={activeTab === 'wholesale-return' ? 'active' : ''}
            onClick={() => setActiveTab('wholesale-return')}
          >
            {t('document-list.tabs.purchase-return', 'Возврат закупок')}
          </button>
          <button
            className={activeTab === 'purchase' ? 'active' : ''}
            onClick={() => setActiveTab('purchase')}
          >
            {t('document-list.tabs.shipment', 'Отгрузки')}
          </button>
          <button
            className={activeTab === 'purchase-return' ? 'active' : ''}
            onClick={() => setActiveTab('purchase-return')}
          >
            {t('document-list.tabs.shipment-return', 'Возврат отгрузок')}
          </button>
          <button
            className={activeTab === 'payment' ? 'active' : ''}
            onClick={() => setActiveTab('payment')}
          >
            {t('document-list.tabs.payment', 'Платежи')}
          </button>
          <button
            className={activeTab === 'balance' ? 'active' : ''}
            onClick={() => setActiveTab('balance')}
          >
            {t('document-list.tabs.balance', 'Баланс')}
          </button>
        </div>

        <div className="date-filter-section">
          <button
            className="calendar-button"
            onClick={() => {
              // When opening the picker, initialize with currently applied dates
              setStartDate(appliedStartDate)
              setEndDate(appliedEndDate)
              setShowDatePicker(!showDatePicker)
            }}
            title={t('document-list.date-picker.title', 'Выбрать период')}
          >
            📅
          </button>
          {showDatePicker && (
            <div className="date-picker-popup">
              <div className="date-picker-header">
                <span>{t('document-list.date-picker.select-period', 'Выберите период')}</span>
                <button className="close-button" onClick={() => setShowDatePicker(false)}>×</button>
              </div>
              <div className="date-inputs">
                <div className="date-input-group">
                  <label>{t('document-list.date-picker.from', 'С:')}</label>
                  <input
                    type="date"
                    value={startDate}
                    onChange={(e) => setStartDate(e.target.value)}
                    max={endDate}
                  />
                </div>
                <div className="date-input-group">
                  <label>{t('document-list.date-picker.to', 'По:')}</label>
                  <input
                    type="date"
                    value={endDate}
                    onChange={(e) => setEndDate(e.target.value)}
                    min={startDate}
                  />
                </div>
              </div>
              <div className="date-picker-actions">
                <button className="reset-button" onClick={resetToCurrentMonth}>
                  {t('document-list.date-picker.current-month', 'Текущий месяц')}
                </button>
                <button className="apply-button" onClick={handleDateChange}>
                  {t('document-list.date-picker.apply', 'Применить')}
                </button>
              </div>
            </div>
          )}
          {!showDatePicker && (
            <div className="date-range-display">
              {new Date(appliedStartDate).toLocaleDateString('ru-RU', { day: '2-digit', month: '2-digit' })} - {new Date(appliedEndDate).toLocaleDateString('ru-RU', { day: '2-digit', month: '2-digit', year: 'numeric' })}
            </div>
          )}
          {Object.keys(documentTotals).length > 0 && (
            <button
              className={`totals-toggle-button-icon ${showTotalsSection ? 'active' : ''}`}
              onClick={() => setShowTotalsSection(!showTotalsSection)}
              title={t('document-list.totals-toggle.title', 'Итого по типам документов')}
            >
              📊
            </button>
          )}
        </div>
      </div>

      {/* Document Type Totals Section */}
      {showTotalsSection && Object.keys(documentTotals).length > 0 && (
        <div className="document-totals-section">
          <div className="totals-grid">
            {Object.entries(documentTotals).map(([type, currencyTotals]) => {
              const typeLabels: { [key: string]: string } = {
                'purchase': t('document-list.totals.shipment', 'Отгрузки'),  // System purchase -> Partner sees shipment
                'purchase-return': 'Возврат отгрузок',  // System purchase return -> Partner sees shipment return
                'wholesale': t('document-list.totals.purchase', 'Закупки'),  // System wholesale -> Partner sees purchase
                'wholesale-return': t('document-list.totals.purchase-return', 'Возврат закупок'),  // System wholesale return -> Partner sees purchase return
                'payment': t('document-list.totals.payment', 'Платежи')
              }

              const typeLabel = typeLabels[type] || type
              const hasTotals = Object.keys(currencyTotals).length > 0 &&
                Object.values(currencyTotals).some(v => v !== 0)

              if (!hasTotals) return null

              return (
                <div key={type} className="total-item">
                  <div className="total-item-label">{typeLabel}:</div>
                  <div className="total-item-amounts">
                    {Object.entries(currencyTotals)
                      .filter(([_, amount]) => amount !== 0)
                      .map(([currency, amount]) => (
                        <span key={currency} className="total-amount-item">
                          {formatNumber(amount)} {currency}
                        </span>
                      ))}
                  </div>
                </div>
              )
            })}
          </div>
        </div>
      )}

      {activeTab === 'balance' ? (
        <PartnerBalance
          telegramUserId={telegramUserId}
          partnerId={partnerId}
          startDate={appliedStartDate}
          endDate={appliedEndDate}
          botName={botName}
        />
      ) : isLoading ? (
        <div className="loading-state">{t('document-list.loading', 'Loading...')}</div>
      ) : error ? (
        <div className="error-state">{error}</div>
      ) : documents.length === 0 ? (
        <div className="empty-state">{t('document-list.empty.no-documents', 'No documents found')}</div>
      ) : (
        <div className="documents">
          {documents.map((doc) => (
            <DocumentCard
              key={doc.id}
              document={doc}
              type={activeTab}
              formatDate={formatDate}
              onClick={(() => {
                if (activeTab === 'purchase' || activeTab === 'purchase-return' || activeTab === 'wholesale' || activeTab === 'wholesale-return') {
                  return () => setSelectedDocument({ id: doc.id, type: activeTab })
                }
                return undefined
              })()}
            />
          ))}
        </div>
      )}
    </div>
  )
}

export default DocumentList
